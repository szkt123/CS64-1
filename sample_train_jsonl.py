import json
import random
from pathlib import Path

input_path = Path("./data/splits/train.jsonl")
output_path = Path("./data/splits/train_3000.jsonl")

sample_size = 3000
seed = 42

random.seed(seed)

with input_path.open("r", encoding="utf-8") as f:
    lines = f.readlines()

total = len(lines)
print(f"total lines: {total}")

if total <= sample_size:
    sampled = lines
    print("dataset smaller than sample size, keep all lines")
else:
    sampled = random.sample(lines, sample_size)

with output_path.open("w", encoding="utf-8") as f:
    f.writelines(sampled)

print(f"saved to: {output_path}")
print(f"sampled size: {len(sampled)}")