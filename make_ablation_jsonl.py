import argparse
import json
import re
from pathlib import Path


ABLATION_SETTINGS = [
    "image_only",
    "image_caption",
    "image_caption_context",
    "full_raw",
    "full",
]


def read_jsonl(path):
    rows = []
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))

    return rows


def write_jsonl(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def clean_text(text):
    if text is None:
        return ""

    text = str(text)

    # 去掉 URL
    text = re.sub(r"http\S+", " ", text)

    # 去掉引用标记，例如 [1], [2, 3]
    text = re.sub(r"\[[0-9,\s]+\]", " ", text)

    # 去掉多余空格
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_paragraphs(value):
    """
    把 nearby_context / citing_paragraphs 统一转成 list[str]
    """
    if value is None:
        return []

    if isinstance(value, list):
        paragraphs = value
    else:
        paragraphs = [value]

    cleaned = []

    for p in paragraphs:
        if isinstance(p, dict):
            p = " ".join(str(v) for v in p.values())

        p = clean_text(p)

        if len(p) >= 20:
            cleaned.append(p)

    return cleaned


def get_caption_words(row):
    caption = clean_text(row.get("caption_text", ""))
    words = re.findall(r"[a-zA-Z]{3,}", caption.lower())
    return set(words)


def paragraph_score(paragraph, caption_words):
    """
    给上下文段落打分：
    1. 和 caption 词重合越多越好
    2. 出现 figure / fig / panel 等词更相关
    3. 太短或太长都不优先
    """
    p_lower = paragraph.lower()
    words = set(re.findall(r"[a-zA-Z]{3,}", p_lower))

    overlap_score = len(words & caption_words)

    figure_score = 0
    if re.search(r"\b(fig|figure|panel|plot|chart|graph|table)\b", p_lower):
        figure_score += 3

    length_score = 0
    if 50 <= len(paragraph) <= 900:
        length_score += 1

    return overlap_score + figure_score + length_score


def select_relevant_paragraphs(row, field_name, max_items=3, max_chars=1200):
    """
    从 citing_paragraphs / nearby_context 中选择最相关的几段，
    避免 full 输入过长、噪声过多。
    """
    paragraphs = normalize_paragraphs(row.get(field_name, []))

    if not paragraphs:
        return []

    caption_words = get_caption_words(row)

    scored = []
    for p in paragraphs:
        score = paragraph_score(p, caption_words)
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected = []
    total_chars = 0

    for score, p in scored:
        if total_chars + len(p) > max_chars:
            continue

        selected.append(p)
        total_chars += len(p)

        if len(selected) >= max_items:
            break

    return selected


def apply_ablation(row, setting):
    row = dict(row)

    # 防止字段不存在时报错
    row.setdefault("caption_text", "")
    row.setdefault("citing_paragraphs", [])
    row.setdefault("nearby_context", [])
    row.setdefault("abstract", "")
    row.setdefault("section_title", "")

    if setting == "image_only":
        # 只保留图片，清空所有文本信息
        row["caption_text"] = ""
        row["citing_paragraphs"] = []
        row["nearby_context"] = []
        row["abstract"] = ""
        row["section_title"] = ""

    elif setting == "image_caption":
        # 保留图片和 caption
        row["caption_text"] = clean_text(row.get("caption_text", ""))
        row["citing_paragraphs"] = []
        row["nearby_context"] = []
        row["abstract"] = ""
        row["section_title"] = ""

    elif setting == "image_caption_context":
        # 保留图片、caption、citing_paragraphs
        # 不加入 nearby_context / abstract / section_title
        row["caption_text"] = clean_text(row.get("caption_text", ""))
        row["citing_paragraphs"] = select_relevant_paragraphs(
            row,
            "citing_paragraphs",
            max_items=3,
            max_chars=1200,
        )
        row["nearby_context"] = []
        row["abstract"] = ""
        row["section_title"] = ""

    elif setting == "full_raw":
        # 原始 full，不做去噪，用来和 denoised full 对比
        pass

    elif setting == "full":
        # 去噪后的 full：
        # 保留 caption + citing_paragraphs + 相关 nearby_context
        # 去掉 abstract 和 section_title
        row["caption_text"] = clean_text(row.get("caption_text", ""))

        row["citing_paragraphs"] = select_relevant_paragraphs(
            row,
            "citing_paragraphs",
            max_items=3,
            max_chars=1200,
        )

        row["nearby_context"] = select_relevant_paragraphs(
            row,
            "nearby_context",
            max_items=2,
            max_chars=800,
        )

        row["abstract"] = ""
        row["section_title"] = ""

        row["ablation_note"] = "denoised_full_caption_citing_nearby_without_abstract_section"

    else:
        raise ValueError(f"Unknown setting: {setting}")

    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    args = parser.parse_args()

    for setting in ABLATION_SETTINGS:
        for split in ["train", "val", "test"]:
            input_path = Path(args.input_dir) / f"{split}.jsonl"
            output_path = Path(args.output_dir) / setting / f"{split}.jsonl"

            rows = read_jsonl(input_path)
            new_rows = [apply_ablation(row, setting) for row in rows]
            write_jsonl(new_rows, output_path)

            print(f"{setting}/{split}: {len(new_rows)} samples -> {output_path}")


if __name__ == "__main__":
    main()