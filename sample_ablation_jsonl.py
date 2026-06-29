from pathlib import Path

settings = [
    "image_only",
    "image_caption",
    "image_caption_context",
    "full",
]

sample_size = 50

# 从已经修复本地图片路径后的 ablation 数据中抽样
input_root = Path("data/ablation_mixed_local")

# 输出到新的小样本文件夹
output_root = Path("data/ablation_mixed_local_sample")

for setting in settings:
    for split in ["train", "val", "test"]:
        input_path = input_root / setting / f"{split}.jsonl"
        output_path = output_root / setting / f"{split}.jsonl"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with input_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        sampled = lines[:sample_size]

        with output_path.open("w", encoding="utf-8") as f:
            f.writelines(sampled)

        print(f"{setting}/{split}: {len(sampled)} -> {output_path}")