import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.dataset import DIMENSIONS
from src.utils.io import ensure_dir, read_jsonl, write_json
from src.utils.export_data import flatten_metrics, write_csv_file, write_json_file


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--pred_jsonl', required=True)
    p.add_argument('--output_dir', required=True)
    return p.parse_args()


def main():
    args = parse_args()
    ensure_dir(args.output_dir)
    rows = read_jsonl(args.pred_jsonl)
    df = pd.DataFrame(rows)
    summary = {}
    scatter_rows = []
    wide_rows = []
    for idx, row in df.iterrows():
        base = {
            "row_index": idx,
            "paper_id": row.get("paper_id"),
            "figure_id": row.get("figure_id"),
            "figure_type": row.get("figure_type"),
        }
        for dim in DIMENSIONS:
            base[f"gold_{dim}"] = row.get("gold_scores", {}).get(dim)
            base[f"pred_{dim}"] = row.get("pred_scores", {}).get(dim)
            if base[f"gold_{dim}"] is not None and base[f"pred_{dim}"] is not None:
                base[f"error_{dim}"] = float(base[f"pred_{dim}"]) - float(base[f"gold_{dim}"])
        wide_rows.append(base)

    for dim in DIMENSIONS:
        gold = df['gold_scores'].apply(lambda x: x[dim]).astype(float).to_numpy()
        pred = df['pred_scores'].apply(lambda x: x[dim]).astype(float).to_numpy()
        summary[dim] = {
            'mae': float(mean_absolute_error(gold, pred)),
            'mse': float(mean_squared_error(gold, pred)),
            'spearman': float(0.0 if np.isnan(spearmanr(gold, pred).statistic) else spearmanr(gold, pred).statistic),
        }
        for idx, (g, p_) in enumerate(zip(gold, pred)):
            source = df.iloc[idx]
            scatter_rows.append({
                'row_index': idx,
                'paper_id': source.get('paper_id'),
                'figure_id': source.get('figure_id'),
                'dimension': dim,
                'gold': float(g),
                'pred': float(p_),
                'error': float(p_ - g),
            })
        plt.figure(figsize=(6, 5))
        plt.scatter(gold, pred)
        plt.xlabel('Gold')
        plt.ylabel('Pred')
        plt.title(f'{dim}: Gold vs Pred')
        plt.tight_layout()
        plt.savefig(os.path.join(args.output_dir, f'scatter_{dim}.png'))
        plt.close()
    write_json(os.path.join(args.output_dir, 'summary.json'), summary)
    export_dir = os.path.join(args.output_dir, 'visualization_data')
    write_json_file(os.path.join(export_dir, 'regression_summary.json'), summary)
    write_csv_file(os.path.join(export_dir, 'regression_summary.csv'), flatten_metrics(summary))
    write_json_file(os.path.join(export_dir, 'scatter_points.json'), scatter_rows)
    write_csv_file(os.path.join(export_dir, 'scatter_points.csv'), scatter_rows)
    write_csv_file(os.path.join(export_dir, 'prediction_details_wide.csv'), wide_rows)
    write_json_file(os.path.join(export_dir, 'prediction_details_wide.json'), wide_rows)


if __name__ == '__main__':
    main()
