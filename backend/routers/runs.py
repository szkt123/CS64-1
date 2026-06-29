from fastapi import APIRouter, HTTPException
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.services.run_manager import run_manager
from src.dataset import DIMENSIONS

router = APIRouter(prefix='/api/runs', tags=['runs'])


@router.get('')
def list_runs():
    return [
        {
            'run_id': x.run_id,
            'status': x.status,
            'output_dir': x.output_dir,
            'current_epoch': x.current_epoch,
            'total_epochs': x.total_epochs,
            'best_val': x.best_val,
        }
        for x in run_manager.list_runs()
    ]


@router.get('/{run_id}/history')
def get_history(run_id: str):
    state = run_manager.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail='Run not found')
    return run_manager.load_history(run_id)


@router.get('/{run_id}/predictions')
def get_predictions(run_id: str):
    state = run_manager.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail='Run not found')
    return run_manager.load_predictions(run_id)


@router.get('/{run_id}/summary')
def get_summary(run_id: str):
    rows = run_manager.load_predictions(run_id)
    if not rows:
        return {'summary': {}, 'count': 0}
    summary = {}
    for dim in DIMENSIONS:
        gold = np.array([float(r['gold_scores'][dim]) for r in rows])
        pred = np.array([float(r['pred_scores'][dim]) for r in rows])
        stat = spearmanr(gold, pred).statistic
        if stat is None or np.isnan(stat):
            stat = 0.0
        summary[dim] = {
            'mae': float(mean_absolute_error(gold, pred)),
            'mse': float(mean_squared_error(gold, pred)),
            'spearman': float(stat),
        }
    return {'summary': summary, 'count': len(rows)}
