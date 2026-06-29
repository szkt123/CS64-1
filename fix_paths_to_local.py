import json
import re
from pathlib import Path

# 改成你电脑上真实的原始数据根目录
# 这个目录下面应该有 ICLR/2024/...
LOCAL_DATA_ROOT = Path(r"C:/Users/yoyo/Desktop/data_v1/data")

OLD_PREFIXES = [
    "/Volumes/JHAO/data_v1",
    "Volumes/JHAO/data_v1",
    "\\Volumes\\JHAO\\data_v1",
]

input_files = [
    "data/training_data.jsonl",
    "data/predictions_data_v1.jsonl",
]

paper_dir_cache = {}


def norm_path(p: str) -> str:
    return (p or "").replace("\\", "/")


def find_by_flat_name(filename: str):
    """
    处理这种路径：
    figures/ICLR_2024_04640_fig_04.png

    转换成查找：
    LOCAL_DATA_ROOT/ICLR/2024/04640_xxx/figures/fig_04.png
    """
    m = re.match(r"(ICLR)_(\d{4})_(\d+)_fig_(\d+)\.png$", filename)
    if not m:
        return None

    venue, year, paper_id, fig_no = m.groups()
    fig_file = f"fig_{fig_no}.png"

    year_dir = LOCAL_DATA_ROOT / venue / year
    if not year_dir.exists():
        return None

    cache_key = (venue, year, paper_id)
    if cache_key not in paper_dir_cache:
        candidates = list(year_dir.glob(f"{paper_id}_*"))
        paper_dir_cache[cache_key] = candidates[0] if candidates else None

    paper_dir = paper_dir_cache[cache_key]
    if paper_dir is None:
        return None

    candidate = paper_dir / "figures" / fig_file
    return candidate if candidate.exists() else None


def find_by_raw_structure(path_str: str):
    """
    处理这种路径：
    /Volumes/JHAO/data_v1/ICLR/2024/06887_xxx/figures/fig_04.png

    或者已经被部分替换成：
    C:/Users/yoyo/Desktop/data_v1/data/ICLR/2024/...
    """
    p = norm_path(path_str)
    parts = p.split("/")

    try:
        venue_idx = parts.index("ICLR")
        venue = parts[venue_idx]
        year = parts[venue_idx + 1]
        paper_folder = parts[venue_idx + 2]
        fig_file = parts[-1]
    except Exception:
        return None

    paper_id = paper_folder.split("_")[0]
    year_dir = LOCAL_DATA_ROOT / venue / year

    if not year_dir.exists():
        return None

    cache_key = (venue, year, paper_id)
    if cache_key not in paper_dir_cache:
        candidates = list(year_dir.glob(f"{paper_id}_*"))
        paper_dir_cache[cache_key] = candidates[0] if candidates else None

    paper_dir = paper_dir_cache[cache_key]
    if paper_dir is None:
        return None

    candidate = paper_dir / "figures" / fig_file
    return candidate if candidate.exists() else None


def fix_one_path(old_path: str) -> str:
    old_norm = norm_path(old_path)

    # 1. 如果原路径本身已经存在，直接保留
    if Path(old_path).exists():
        return old_path

    # 2. 修复 /Volumes/JHAO/data_v1 前缀
    for old_prefix in OLD_PREFIXES:
        old_prefix_norm = norm_path(old_prefix)
        if old_norm.startswith(old_prefix_norm):
            rel_path = old_norm[len(old_prefix_norm):].lstrip("/")
            candidate = LOCAL_DATA_ROOT / rel_path
            if candidate.exists():
                return str(candidate).replace("\\", "/")

    # 3. 处理 figures/ICLR_2024_xxxxx_fig_xx.png 这种扁平路径
    if old_norm.startswith("figures/"):
        filename = Path(old_norm).name
        found = find_by_flat_name(filename)
        if found:
            return str(found).replace("\\", "/")

    # 4. 处理任意包含 ICLR/2024/.../figures/fig_xx.png 的路径
    found = find_by_raw_structure(old_norm)
    if found:
        return str(found).replace("\\", "/")

    # 5. 实在找不到，保留原路径
    return old_path


for input_file in input_files:
    input_path = Path(input_file)

    # 这里直接覆盖旧的 _local 文件
    output_path = input_path.with_name(input_path.stem + "_local.jsonl")

    total = 0
    fixed = 0
    still_missing = 0

    with input_path.open("r", encoding="utf-8") as fin, \
         output_path.open("w", encoding="utf-8") as fout:

        for line in fin:
            if not line.strip():
                continue

            obj = json.loads(line)
            old_path = obj.get("figure_image_path", "")
            new_path = fix_one_path(old_path)

            if new_path != old_path:
                fixed += 1

            if not Path(new_path).exists():
                still_missing += 1
                if still_missing <= 10:
                    print("Still missing:", new_path)

            obj["figure_image_path"] = new_path
            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            total += 1

    print(f"\nSaved: {output_path}")
    print(f"Total: {total}")
    print(f"Fixed: {fixed}")
    print(f"Still missing: {still_missing}")