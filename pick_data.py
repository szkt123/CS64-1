import json
from pathlib import Path

train_path = Path("./data/splits/train.jsonl")
subset_path = Path("./data/splits/train_3000.jsonl")
output_path = Path("./data/splits/train_rest.jsonl")

KEY1 = "paper_id"
KEY2 = "figure_id"

subset_keys = set()

with subset_path.open("r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        key = (obj[KEY1], obj[KEY2])
        subset_keys.add(key)

print(f"subset size: {len(subset_keys)}")

count = 0

with train_path.open("r", encoding="utf-8") as fin, \
     output_path.open("w", encoding="utf-8") as fout:

    for line in fin:
        obj = json.loads(line)
        key = (obj[KEY1], obj[KEY2])

        if key not in subset_keys:
            fout.write(line)
            count += 1

print(f"saved {count} samples to {output_path}")