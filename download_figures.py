"""
Download figure images from Hugging Face to frontend/public/figures/.

Usage:
    pip install huggingface_hub
    python download_figures.py --repo YOUR_USERNAME/capstone-figures

For private repos, login first:
    huggingface-cli login
"""

import argparse
import sys
from pathlib import Path

try:
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
except ImportError:
    print("Install: pip install huggingface_hub")
    sys.exit(1)

DEFAULT_OUT = Path(__file__).parent / "frontend" / "public" / "figures"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True, help="HF repo id, e.g. username/capstone-figures")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory (default: frontend/public/figures)")
    p.add_argument("--resume", action="store_true", default=True, help="Skip files already downloaded (default: on)")
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    api = HfApi()

    print(f"Fetching file list from https://huggingface.co/datasets/{args.repo} ...")
    all_files = [
        f.rfilename
        for f in api.list_repo_tree(repo_id=args.repo, repo_type="dataset", recursive=True)
        if f.rfilename.startswith("figures/") and f.rfilename.endswith(".png")
    ]
    print(f"Found {len(all_files)} figures in repo")

    if args.resume:
        existing = {f.name for f in out_dir.glob("*.png")}
        to_download = [f for f in all_files if Path(f).name not in existing]
        print(f"Already have {len(existing)}, downloading {len(to_download)} new files")
    else:
        to_download = all_files

    if not to_download:
        print("Nothing to download.")
        return

    for i, repo_path in enumerate(to_download, 1):
        fname = Path(repo_path).name
        dest = out_dir / fname
        hf_hub_download(
            repo_id=args.repo,
            filename=repo_path,
            repo_type="dataset",
            local_dir=str(out_dir.parent.parent),
        )
        if i % 100 == 0 or i == len(to_download):
            print(f"  {i}/{len(to_download)} downloaded")

    print(f"\nDone. Figures saved to: {out_dir}")


if __name__ == "__main__":
    main()
