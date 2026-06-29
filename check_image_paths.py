import json
from pathlib import Path

jsonl_path = Path("data/ablation_mixed_local_sample/image_only/train.jsonl")

total = 0
missing = 0

with jsonl_path.open("r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue

        obj = json.loads(line)
        image_path = Path(obj["figure_image_path"])

        total += 1

        if not image_path.exists():
            missing += 1
            print("Missing:", image_path)

            if missing >= 10:
                break

print("Checked:", total)
print("Missing:", missing)