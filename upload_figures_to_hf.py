"""
Upload figure images to a Hugging Face Dataset repository.

Usage:
    pip install huggingface_hub
    huggingface-cli login

    # First run: create repo and upload everything
    python upload_figures_to_hf.py --repo your-username/capstone-figures

    # Resume interrupted upload (skips already-uploaded files)
    python upload_figures_to_hf.py --repo your-username/capstone-figures --resume
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("Install: pip install huggingface_hub")
    sys.exit(1)

FIGURES_DIR = Path(__file__).parent.parent / "data_source" / "figures"

DATASET_CARD = """\
---
license: cc-by-4.0
task_categories:
- image-classification
language:
- en
tags:
- scientific-figures
- figure-quality
- multimodal
---

# Capstone Figure Dataset

Scientific figure images extracted from ICLR 2024, ICLR 2025, NeurIPS 2023/2024,
ICML 2023/2024 papers. Used for multidimensional figure quality assessment.

## Files

Each image is named `{VENUE}_{YEAR}_{ID:05d}_fig_{N}.png`.

## Annotation data

JSONL annotation files are available in the companion GitHub repo.

## Paper source

Papers can be re-downloaded with `download_papers.py` from the GitHub repo.
"""


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="HF repo id, e.g. username/capstone-figures")
    p.add_argument("--figures-dir", default=str(FIGURES_DIR), help="Local figures directory")
    p.add_argument("--resume", action="store_true", help="Skip files already in the repo")
    p.add_argument("--private", action="store_true", help="Create a private repo")
    return p.parse_args()


def main():
    args = parse_args()
    figures_dir = Path(args.figures_dir)

    if not figures_dir.exists():
        print(f"Figures directory not found: {figures_dir}")
        sys.exit(1)

    images = sorted(figures_dir.glob("*.png"))
    if not images:
        print(f"No PNG files found in {figures_dir}")
        sys.exit(1)

    print(f"Found {len(images)} images in {figures_dir}")

    api = HfApi()

    # Create repo if it doesn't exist
    create_repo(
        repo_id=args.repo,
        repo_type="dataset",
        exist_ok=True,
        private=args.private,
    )
    print(f"Repo ready: https://huggingface.co/datasets/{args.repo}")

    # Upload dataset card
    api.upload_file(
        path_or_fileobj=DATASET_CARD.encode(),
        path_in_repo="README.md",
        repo_id=args.repo,
        repo_type="dataset",
    )

    # Get existing files for resume mode
    existing = set()
    if args.resume:
        print("Fetching existing file list for resume...")
        existing = {
            f.rfilename
            for f in api.list_repo_tree(repo_id=args.repo, repo_type="dataset")
        }
        print(f"  {len(existing)} files already uploaded")

    # Upload images in batches of 100
    to_upload = [img for img in images if f"figures/{img.name}" not in existing]
    print(f"Uploading {len(to_upload)} files...")

    batch_size = 100
    for i in range(0, len(to_upload), batch_size):
        batch = to_upload[i : i + batch_size]
        api.upload_folder(
            folder_path=str(figures_dir),
            repo_id=args.repo,
            repo_type="dataset",
            path_in_repo="figures",
            allow_patterns=[img.name for img in batch],
        )
        done = min(i + batch_size, len(to_upload))
        print(f"  {done}/{len(to_upload)} uploaded")

    print(f"\nDone. View at: https://huggingface.co/datasets/{args.repo}")


if __name__ == "__main__":
    main()
