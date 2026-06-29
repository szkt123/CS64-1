import asyncio
import json
import re
import subprocess
import sys
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, List, Optional

from src.utils.io import ensure_dir, read_json, read_jsonl

ANSI_ESCAPE_RE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
EPOCH_RE = re.compile(r'\[epoch\s+(\d+)/(\d+)\]\s+step\s+(\d+)/(\d+)')
LOSS_RE = re.compile(r'loss=([0-9]*\.?[0-9]+)')
BEST_RE = re.compile(r'best_val[=:]\s*([0-9]*\.?[0-9]+)', re.IGNORECASE)


@dataclass
class RunState:
    run_id: str
    output_dir: str
    status: str = 'created'
    pid: Optional[int] = None
    current_epoch: int = 0
    total_epochs: int = 0
    current_step: int = 0
    total_steps: int = 0
    train_loss: Optional[float] = None
    val_loss: Optional[float] = None
    best_val: Optional[float] = None
    logs: Deque[str] = field(default_factory=lambda: deque(maxlen=1200))
    process: Optional[subprocess.Popen] = None
    batch_history: List[dict] = field(default_factory=list)
    epoch_history: List[dict] = field(default_factory=list)
    updated_at: float = 0.0


class RunManager:
    def __init__(self) -> None:
        self.runs: Dict[str, RunState] = {}

    def list_runs(self) -> List[RunState]:
        return list(self.runs.values())

    def get(self, run_id: str) -> Optional[RunState]:
        return self.runs.get(run_id)

    async def start_training(self, payload: dict, project_root: str) -> RunState:
        cmd = [
            sys.executable, 'train.py',
            '--train_jsonl', payload['train_jsonl'],
            '--val_jsonl', payload['val_jsonl'],
            '--output_dir', payload['output_dir'],
            '--batch_size', str(payload['batch_size']),
            '--epochs', str(payload['epochs']),
            '--lr', str(payload['lr']),
            '--weight_decay', str(payload['weight_decay']),
            '--dropout', str(payload['dropout']),
            '--proj_dim', str(payload['proj_dim']),
            '--cube_tokens', str(payload.get('cube_tokens', 4)),
            '--cube_depth', str(payload.get('cube_depth', 3)),
            '--mixing_expansion', str(payload.get('mixing_expansion', 2.0)),
            '--max_text_length', str(payload['max_text_length']),
            '--text_model_name', payload['text_model_name'],
            '--image_model_name', payload['image_model_name'],
            '--seed', str(payload['seed']),
            '--num_workers', str(payload['num_workers']),
            '--ranking_weight', str(payload['ranking_weight']),
            '--log_every', str(payload.get('log_every', 10)),
            '--emit_every', str(payload.get('emit_every', 1)),
            '--cross_attention_heads', str(payload.get('cross_attention_heads', 4)),
            '--cross_attention_layers', str(payload.get('cross_attention_layers', 1)),
        ]
        for flag in [
            'verify_images',
            'include_weak_labels',
            'use_ranking_loss',
            'freeze_text_encoder',
            'freeze_image_encoder',
            'save_every_epoch',
            'use_bidirectional_cross_attention',
        ]:
            if payload.get(flag):
                cmd.append(f'--{flag}')
        return await self._start_process(payload['output_dir'], cmd, project_root, task_label='training')

    async def start_test_prediction(self, payload: dict, project_root: str) -> RunState:
        output_path = Path(payload['output_dir']) / payload.get('output_filename', 'test_predictions.jsonl')
        cmd = [
            sys.executable, 'predict.py',
            '--checkpoint', payload['checkpoint'],
            '--input_jsonl', payload['input_jsonl'],
            '--output_jsonl', str(output_path),
            '--batch_size', str(payload.get('batch_size', 4)),
            '--num_workers', str(payload.get('num_workers', 0)),
            '--device', payload.get('device', 'auto'),
        ]
        for flag in ['verify_images', 'include_weak_labels']:
            if payload.get(flag):
                cmd.append(f'--{flag}')
        return await self._start_process(payload['output_dir'], cmd, project_root, task_label='test prediction')

    async def _start_process(self, output_dir: str, cmd: list, project_root: str, task_label: str) -> RunState:
        run_id = uuid.uuid4().hex[:10]
        ensure_dir(output_dir)
        state = RunState(run_id=run_id, output_dir=output_dir, status='starting')
        self.runs[run_id] = state

        env = dict(**__import__('os').environ)
        env['PYTHONUNBUFFERED'] = '1'
        env['TOKENIZERS_PARALLELISM'] = 'false'

        state.logs.append(f'[manager] starting {task_label} process in: {project_root}')
        state.logs.append(f"[manager] cmd: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=env,
        )
        state.process = process
        state.pid = process.pid
        state.status = 'running'
        state.logs.append(f'[manager] pid={process.pid}')
        state.updated_at = asyncio.get_event_loop().time()

        if process.stdout is not None:
            asyncio.create_task(asyncio.to_thread(self._capture_stream, process.stdout, state, 'stdout'))
        if process.stderr is not None:
            asyncio.create_task(asyncio.to_thread(self._capture_stream, process.stderr, state, 'stderr'))
        asyncio.create_task(self._wait_for_process(state))
        return state

    def _touch(self, state: RunState) -> None:
        try:
            state.updated_at = asyncio.get_event_loop().time()
        except RuntimeError:
            state.updated_at = 0.0

    def _normalize_line(self, line: str) -> str:
        line = line.replace('\r', '')
        line = ANSI_ESCAPE_RE.sub('', line)
        return line.strip()

    def _should_skip_log_line(self, line: str) -> bool:
        if not line:
            return True
        noisy_patterns = [
            'cls.predictions.transform',
            'text_model.encoder.layers',
            'text_model.embeddings',
            'position_embedding.weight',
            'pooler.dense',
            'LOAD REPORT',
            'Some weights of',
            'Weights from pretrained model not used',
            'Weights of',
        ]
        return any(p in line for p in noisy_patterns)

    def _append_log(self, state: RunState, line: str) -> None:
        if line:
            state.logs.append(line)
            self._touch(state)

    def _capture_stream(self, stream, state: RunState, prefix: str) -> None:
        try:
            for raw_line in iter(stream.readline, ''):
                if not raw_line:
                    break
                line = self._normalize_line(raw_line)
                if not line:
                    continue

                if line.startswith('EVENT_JSON:'):
                    try:
                        event = json.loads(line[len('EVENT_JSON:'):])
                        self._apply_event(state, event)
                    except Exception as exc:
                        self._append_log(state, f'[manager] failed to parse event: {exc}')
                    continue

                if self._should_skip_log_line(line):
                    continue

                if prefix == 'stderr':
                    lowered = line.lower()
                    if 'warning' in lowered or 'not installed' in lowered or 'unauthenticated requests' in lowered:
                        self._append_log(state, f'[warning] {line}')
                    else:
                        self._append_log(state, f'[stderr] {line}')
                else:
                    self._append_log(state, line)

                self._parse_progress_line(state, line)
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def _parse_progress_line(self, state: RunState, line: str) -> None:
        epoch_step_match = EPOCH_RE.search(line)
        if epoch_step_match:
            state.current_epoch = int(epoch_step_match.group(1))
            state.total_epochs = int(epoch_step_match.group(2))
            state.current_step = int(epoch_step_match.group(3))
            state.total_steps = int(epoch_step_match.group(4))

        loss_match = LOSS_RE.search(line)
        if loss_match:
            state.train_loss = float(loss_match.group(1))

        best_match = BEST_RE.search(line)
        if best_match:
            state.best_val = float(best_match.group(1))

        self._touch(state)

    def _apply_event(self, state: RunState, event: dict) -> None:
        event_type = event.get('type')
        if event_type == 'batch':
            state.current_epoch = event.get('epoch', state.current_epoch)
            state.total_epochs = event.get('total_epochs', state.total_epochs)
            state.current_step = event.get('step', state.current_step)
            state.total_steps = event.get('total_steps', state.total_steps)
            state.train_loss = event.get('loss', state.train_loss)
            global_step = max(event.get('step', 0), 0)
            if state.total_steps and state.current_epoch:
                global_step = (state.current_epoch - 1) * state.total_steps + state.current_step
            state.batch_history.append({
                'global_step': global_step,
                'epoch': state.current_epoch,
                'step': state.current_step,
                'total_steps': state.total_steps,
                'loss': event.get('loss'),
                'reg_loss': event.get('reg_loss'),
                'rank_loss': event.get('rank_loss'),
                'attn_peak': event.get('attn_peak'),
                'attn_entropy': event.get('attn_entropy'),
            })
            state.batch_history = state.batch_history[-1500:]
        elif event_type == 'epoch_start':
            state.current_epoch = event.get('epoch', state.current_epoch)
            state.total_epochs = event.get('total_epochs', state.total_epochs)
            state.total_steps = event.get('total_steps', state.total_steps)
            state.current_step = 0
        elif event_type == 'epoch_end':
            state.current_epoch = event.get('epoch', state.current_epoch)
            state.total_epochs = event.get('total_epochs', state.total_epochs)
            state.current_step = state.total_steps
            state.train_loss = event.get('train_loss', state.train_loss)
            state.val_loss = event.get('val_loss', state.val_loss)
            state.epoch_history.append({
                'epoch': event.get('epoch'),
                'train_loss': event.get('train_loss'),
                'val_loss': event.get('val_loss'),
                'val_metrics': event.get('val_metrics', {}),
                'metric_snapshot': event.get('metric_snapshot', {}),
                'attn_peak': event.get('attn_peak'),
                'attn_entropy': event.get('attn_entropy'),
            })
            state.epoch_history = state.epoch_history[-300:]
            self._append_log(
                state,
                f"[epoch {event.get('epoch')}] train_loss={event.get('train_loss', 0):.4f} | val_loss={event.get('val_loss', 0):.4f}"
            )
        elif event_type == 'best_checkpoint':
            state.best_val = event.get('best_val', state.best_val)
            self._append_log(state, f"[checkpoint] epoch={event.get('epoch')} | best_val={event.get('best_val', 0):.4f}")
        elif event_type == 'finished':
            state.best_val = event.get('best_val', state.best_val)
            state.status = 'finished'
            self._append_log(state, f"[done] training finished, best_val={event.get('best_val', 0):.4f}")
        elif event_type == 'status':
            stage = event.get('stage')
            if stage:
                state.status = stage
            if event.get('message'):
                self._append_log(state, f"[status] {event.get('message')}")
        elif event_type == 'dataset':
            self._append_log(state, f"[dataset] train={event.get('train_size', 0)}, val={event.get('val_size', 0)}")
        elif event_type == 'config':
            self._append_log(state, f"[config] log_every={event.get('log_every')} | emit_every={event.get('emit_every')}")
        self._touch(state)

    async def _wait_for_process(self, state: RunState) -> None:
        assert state.process is not None
        code = await asyncio.to_thread(state.process.wait)
        if state.status not in {'finished', 'stopped'}:
            state.status = 'finished' if code == 0 else 'failed'
        self._append_log(state, f'[manager] process exited with code {code}')

    async def stop_run(self, run_id: str) -> bool:
        state = self.runs.get(run_id)
        if not state or not state.process:
            return False
        if state.process.poll() is None:
            state.process.terminate()
        state.status = 'stopped'
        self._append_log(state, '[manager] stop signal sent')
        return True

    def load_history(self, run_id: str):
        state = self.runs.get(run_id)
        if not state:
            return {'history': []}
        path = Path(state.output_dir) / 'history.json'
        disk_history = read_json(str(path)) if path.exists() else {'history': []}
        memory_history = state.epoch_history or []
        if len(memory_history) >= len(disk_history.get('history', [])):
            return {'history': memory_history}
        return disk_history

    def load_predictions(self, run_id: str):
        state = self.runs.get(run_id)
        if not state:
            return []
        path = Path(state.output_dir) / 'test_predictions.jsonl'
        return read_jsonl(str(path)) if path.exists() else []


run_manager = RunManager()
