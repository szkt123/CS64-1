import io
from pathlib import Path
from typing import Dict, Any

import torch
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from PIL import Image

from predict import load_model, score_single_image
from backend.schemas.infer import TestPredictStartRequest
from backend.services.run_manager import run_manager
from src.dataset import DIMENSIONS
from src.utils.device import resolve_device, setup_torch_backends

router = APIRouter(prefix='/api/infer', tags=['infer'])

_MODEL_CACHE = {}


def get_cached_model(checkpoint_path: Path, device: torch.device):
    key = (str(checkpoint_path.resolve()), str(device))
    cached = _MODEL_CACHE.get(key)

    if cached is None:
        cached = load_model(str(checkpoint_path), device)
        _MODEL_CACHE[key] = cached

    return cached


def read_image_from_upload(upload_file: UploadFile) -> Image.Image:
    content = upload_file.file.read()
    return Image.open(io.BytesIO(content)).convert('RGB')


def calc_overall_score(scores: Dict[str, float]) -> float:
    values = []
    for dim in DIMENSIONS:
        if dim in scores:
            values.append(float(scores[dim]))

    if not values:
        return 0.0

    return sum(values) / len(values)


def build_dimension_comparison(scores_a: Dict[str, float], scores_b: Dict[str, float]):
    rows = []

    for dim in DIMENSIONS:
        score_a = float(scores_a.get(dim, 0.0))
        score_b = float(scores_b.get(dim, 0.0))
        diff = score_a - score_b

        if abs(diff) < 1e-6:
            winner = 'tie'
        elif diff > 0:
            winner = 'A'
        else:
            winner = 'B'

        rows.append({
            'dimension': dim,
            'score_a': round(score_a, 4),
            'score_b': round(score_b, 4),
            'difference': round(diff, 4),
            'winner': winner,
        })

    return rows


def get_confidence(abs_diff: float) -> str:
    if abs_diff >= 0.75:
        return 'high'
    if abs_diff >= 0.30:
        return 'medium'
    return 'low'


@router.post('/start-test-predict')
async def start_test_predict(payload: TestPredictStartRequest):
    project_root = str(Path(__file__).resolve().parents[2])
    state = await run_manager.start_test_prediction(payload.model_dump(), project_root)

    return {
        'run_id': state.run_id,
        'status': state.status,
        'output_dir': state.output_dir,
    }


@router.post('/score-image')
async def score_image(
    checkpoint: str = Form(...),
    caption_text: str = Form(''),
    context_text: str = Form(''),
    abstract_text: str = Form(''),
    meta_text: str = Form(''),
    image: UploadFile = File(...),
):
    checkpoint_path = Path(checkpoint)

    if not checkpoint_path.exists():
        raise HTTPException(status_code=404, detail='Checkpoint not found')

    content = await image.read()
    pil_image = Image.open(io.BytesIO(content)).convert('RGB')

    device = resolve_device('auto')
    setup_torch_backends(device, allow_tf32=True)

    model, collator, _ = get_cached_model(checkpoint_path, device)

    result = score_single_image(
        model=model,
        collator=collator,
        device=device,
        image=pil_image,
        caption_text=caption_text,
        context_text=context_text,
        abstract_text=abstract_text,
        meta_text=meta_text,
    )

    return result


@router.post('/compare-two-images')
async def compare_two_images(
    checkpoint: str = Form(...),

    a_figure_id: str = Form('Figure A'),
    a_caption_text: str = Form(''),
    a_context_text: str = Form(''),
    a_abstract_text: str = Form(''),
    a_meta_text: str = Form(''),
    a_image: UploadFile = File(...),

    b_figure_id: str = Form('Figure B'),
    b_caption_text: str = Form(''),
    b_context_text: str = Form(''),
    b_abstract_text: str = Form(''),
    b_meta_text: str = Form(''),
    b_image: UploadFile = File(...),
):
    checkpoint_path = Path(checkpoint)

    if not checkpoint_path.exists():
        raise HTTPException(status_code=404, detail='Checkpoint not found')

    try:
        image_a = Image.open(io.BytesIO(await a_image.read())).convert('RGB')
        image_b = Image.open(io.BytesIO(await b_image.read())).convert('RGB')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid image file: {e}')

    device = resolve_device('auto')
    setup_torch_backends(device, allow_tf32=True)

    model, collator, _ = get_cached_model(checkpoint_path, device)

    result_a = score_single_image(
        model=model,
        collator=collator,
        device=device,
        image=image_a,
        caption_text=a_caption_text,
        context_text=a_context_text,
        abstract_text=a_abstract_text,
        meta_text=a_meta_text,
    )

    result_b = score_single_image(
        model=model,
        collator=collator,
        device=device,
        image=image_b,
        caption_text=b_caption_text,
        context_text=b_context_text,
        abstract_text=b_abstract_text,
        meta_text=b_meta_text,
    )

    scores_a = result_a.get('scores', {})
    scores_b = result_b.get('scores', {})

    overall_a = calc_overall_score(scores_a)
    overall_b = calc_overall_score(scores_b)

    diff = overall_a - overall_b
    abs_diff = abs(diff)

    if abs_diff < 1e-6:
        winner = 'tie'
    elif diff > 0:
        winner = 'A'
    else:
        winner = 'B'

    dimension_comparison = build_dimension_comparison(scores_a, scores_b)

    return {
        'winner': winner,
        'score_difference_a_minus_b': round(diff, 4),
        'absolute_score_difference': round(abs_diff, 4),
        'confidence': get_confidence(abs_diff),

        'figure_a': {
            'figure_id': a_figure_id,
            'overall_score': round(overall_a, 4),
            'scores': scores_a,
            'explanation': result_a.get('explanation', {}),
        },

        'figure_b': {
            'figure_id': b_figure_id,
            'overall_score': round(overall_b, 4),
            'scores': scores_b,
            'explanation': result_b.get('explanation', {}),
        },

        'dimension_comparison': dimension_comparison,
    }