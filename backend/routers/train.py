import asyncio
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.schemas.train import TrainStartRequest
from backend.services.run_manager import run_manager

router = APIRouter(prefix='/api/train', tags=['train'])
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@router.post('/start')
async def start_train(payload: TrainStartRequest):
    state = await run_manager.start_training(payload.model_dump(), PROJECT_ROOT)
    return {'run_id': state.run_id, 'status': state.status, 'output_dir': state.output_dir}


@router.get('/status/{run_id}')
async def get_status(run_id: str):
    state = run_manager.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail='Run not found')
    return {
        'run_id': state.run_id,
        'status': state.status,
        'current_epoch': state.current_epoch,
        'total_epochs': state.total_epochs,
        'current_step': state.current_step,
        'total_steps': state.total_steps,
        'train_loss': state.train_loss,
        'val_loss': state.val_loss,
        'best_val': state.best_val,
        'output_dir': state.output_dir,
        'batch_history': state.batch_history[-1200:],
        'epoch_history': state.epoch_history,
        'logs': list(state.logs),
    }


@router.get('/logs/{run_id}')
async def get_logs(run_id: str):
    state = run_manager.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail='Run not found')
    return {'logs': list(state.logs)}


@router.post('/stop/{run_id}')
async def stop_run(run_id: str):
    ok = await run_manager.stop_run(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail='Run not found or not running')
    return {'ok': True}


@router.websocket('/ws/{run_id}')
async def run_ws(websocket: WebSocket, run_id: str):
    await websocket.accept()
    try:
        while True:
            state = run_manager.get(run_id)
            if not state:
                await websocket.send_json({'type': 'error', 'message': 'Run not found'})
                break
            await websocket.send_json({
                'type': 'status',
                'run_id': state.run_id,
                'status': state.status,
                'current_epoch': state.current_epoch,
                'total_epochs': state.total_epochs,
                'current_step': state.current_step,
                'total_steps': state.total_steps,
                'train_loss': state.train_loss,
                'val_loss': state.val_loss,
                'best_val': state.best_val,
                'logs': list(state.logs),
                'batch_history': state.batch_history[-1200:],
                'epoch_history': state.epoch_history,
            })
            if state.status in {'finished', 'failed', 'stopped'}:
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
