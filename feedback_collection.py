import json
from pathlib import Path
import pandas as pd


runs = {
    "image_only": "outputs/ablation_mixed_local_image_only/analysis_human/summary.json",
    "image_caption": "outputs/ablation_mixed_local_image_caption/analysis_human/summary.json",
    "image_caption_context": "outputs/ablation_mixed_local_image_caption_context/analysis_human/summary.json",
    "full": "outputs/ablation_mixed_local_full/analysis_human/summary.json",
}

rows = []

for setting, path in runs.items():
    path = Path(path)

    if not path.exists():
        print(f"Missing: {path}")
        continue

    with path.open("r", encoding="utf-8") as f:
        summary = json.load(f)

    for dim in ["clarity", "relevance", "informativeness", "structure", "macro_avg"]:
        if dim not in summary:
            continue

        metrics = summary[dim]
        rows.append({
            "setting": setting,
            "dimension": dim,
            "mae": metrics.get("mae"),
            "mse": metrics.get("mse"),
            "spearman": metrics.get("spearman"),
        })

df = pd.DataFrame(rows)

output_path = Path("outputs/ablation_human_comparison.csv")
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(df)
print(f"\nSaved to {output_path}")
