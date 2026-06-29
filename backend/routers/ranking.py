from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from scipy.stats import kendalltau, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.services.run_manager import run_manager
from src.dataset import DIMENSIONS

router = APIRouter(prefix='/api/ranking', tags=['ranking'])


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        value = float(value)
        if np.isnan(value):
            return default
        return value
    except Exception:
        return default


def _safe_corr(fn, gold: np.ndarray, pred: np.ndarray) -> float:
    if len(gold) < 2 or len(pred) < 2:
        return 0.0
    try:
        stat = fn(gold, pred).statistic
        if stat is None or np.isnan(stat):
            return 0.0
        return float(stat)
    except Exception:
        return 0.0


def _get_score(row: Dict[str, Any], score_key: str, dim: str) -> float:
    scores = row.get(score_key) or {}
    return _safe_float(scores.get(dim), 0.0)


def _figure_name(row: Dict[str, Any]) -> str:
    return str(row.get('figure_id') or row.get('image_id') or row.get('id') or '')


def _build_regression_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {}
    for dim in DIMENSIONS:
        gold = np.array([_get_score(r, 'gold_scores', dim) for r in rows], dtype=float)
        pred = np.array([_get_score(r, 'pred_scores', dim) for r in rows], dtype=float)
        summary[dim] = {
            'mae': float(mean_absolute_error(gold, pred)) if len(gold) else 0.0,
            'mse': float(mean_squared_error(gold, pred)) if len(gold) else 0.0,
            'spearman': _safe_corr(spearmanr, gold, pred),
            'kendall_tau': _safe_corr(kendalltau, gold, pred),
        }

    if summary:
        summary['macro_avg'] = {
            'mae': float(np.mean([summary[d]['mae'] for d in DIMENSIONS])),
            'mse': float(np.mean([summary[d]['mse'] for d in DIMENSIONS])),
            'spearman': float(np.mean([summary[d]['spearman'] for d in DIMENSIONS])),
            'kendall_tau': float(np.mean([summary[d]['kendall_tau'] for d in DIMENSIONS])),
        }
    return summary


def _pairwise_for_dimension(rows: List[Dict[str, Any]], dim: str, min_diff: float, max_examples: int) -> Dict[str, Any]:
    grouped = defaultdict(list)
    for row in rows:
        paper_id = str(row.get('paper_id') or '')
        if paper_id:
            grouped[paper_id].append(row)

    total = 0
    correct = 0
    pred_tie = 0
    examples = []

    for paper_id, paper_rows in grouped.items():
        if len(paper_rows) < 2:
            continue
        for a, b in combinations(paper_rows, 2):
            gold_a = _get_score(a, 'gold_scores', dim)
            gold_b = _get_score(b, 'gold_scores', dim)
            pred_a = _get_score(a, 'pred_scores', dim)
            pred_b = _get_score(b, 'pred_scores', dim)

            gold_diff = gold_a - gold_b
            pred_diff = pred_a - pred_b
            if abs(gold_diff) <= min_diff:
                continue

            total += 1
            is_correct = bool(np.sign(gold_diff) == np.sign(pred_diff))
            correct += int(is_correct)
            pred_tie += int(pred_diff == 0)

            if len(examples) < max_examples:
                fig_a = _figure_name(a)
                fig_b = _figure_name(b)
                examples.append({
                    'paper_id': paper_id,
                    'dimension': dim,
                    'figure_a': fig_a,
                    'figure_b': fig_b,
                    'human_score_a': round(float(gold_a), 4),
                    'human_score_b': round(float(gold_b), 4),
                    'pred_score_a': round(float(pred_a), 4),
                    'pred_score_b': round(float(pred_b), 4),
                    'human_winner': fig_a if gold_diff > 0 else fig_b,
                    'model_winner': fig_a if pred_diff > 0 else fig_b if pred_diff < 0 else 'tie',
                    'is_correct': is_correct,
                    'caption_a': a.get('caption_text', ''),
                    'caption_b': b.get('caption_text', ''),
                })

    return {
        'valid_pairs': int(total),
        'correct_pairs': int(correct),
        'wrong_pairs': int(total - correct),
        'pred_tie_pairs': int(pred_tie),
        'pairwise_accuracy': float(correct / total) if total else 0.0,
        'examples': examples,
    }


def _add_overall_scores(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched = []
    for row in rows:
        r = dict(row)
        gold_overall = float(np.mean([_get_score(row, 'gold_scores', d) for d in DIMENSIONS]))
        pred_overall = float(np.mean([_get_score(row, 'pred_scores', d) for d in DIMENSIONS]))
        r['gold_scores'] = dict(row.get('gold_scores') or {})
        r['pred_scores'] = dict(row.get('pred_scores') or {})
        r['gold_scores']['overall'] = gold_overall
        r['pred_scores']['overall'] = pred_overall
        enriched.append(r)
    return enriched


@router.get('/{run_id}/analysis')
def get_ranking_analysis(
    run_id: str,
    min_diff: float = Query(0.5, ge=0.0, description='Ignore pairs whose human score difference is not larger than this value.'),
    max_examples: int = Query(200, ge=1, le=1000),
):
    state = run_manager.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail='Run not found')

    rows = run_manager.load_predictions(run_id)
    if not rows:
        raise HTTPException(status_code=404, detail='No prediction file found. Please run Test Predict first.')

    regression_summary = _build_regression_summary(rows)
    enriched_rows = _add_overall_scores(rows)

    pairwise_summary = {}
    examples = []
    for dim in list(DIMENSIONS) + ['overall']:
        result = _pairwise_for_dimension(enriched_rows, dim, min_diff, max_examples)
        pairwise_summary[dim] = {k: v for k, v in result.items() if k != 'examples'}
        examples.extend(result['examples'])

    overall = pairwise_summary.get('overall', {})
    return {
        'run_id': run_id,
        'count': len(rows),
        'min_diff': min_diff,
        'dimensions': list(DIMENSIONS),
        'regression_summary': regression_summary,
        'pairwise_summary': pairwise_summary,
        'pairwise_examples': examples[:max_examples],
        'claim': {
            'title': 'Same-paper figure ranking is supported',
            'text': 'For figures from the same paper, the model compares predicted quality scores and checks whether the predicted order matches the human-labelled order.',
            'overall_pairwise_accuracy': overall.get('pairwise_accuracy', 0.0),
            'overall_valid_pairs': overall.get('valid_pairs', 0),
        },
    }
