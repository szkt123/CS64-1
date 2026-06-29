"""
Download source PDFs for the capstone figure dataset.

Papers are fetched from OpenReview (primary) with arXiv as fallback.
Requires no API keys.

Usage:
    pip install requests tqdm

    # Download all 2294 papers (~12 GB)
    python download_papers.py

    # Download to a custom directory
    python download_papers.py --out /data/papers

    # Smoke-test with 5 papers
    python download_papers.py --limit 5

    # Resume interrupted download (skips existing PDFs)
    python download_papers.py --resume

    # Parallel workers (default 4, increase with care to avoid rate limits)
    python download_papers.py --workers 4
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from tqdm import tqdm
except ImportError:
    import sys
    print("Install: pip install requests tqdm")
    sys.exit(1)

METADATA_FILE = Path(__file__).parent / "paper_metadata.json"
DEFAULT_OUT   = Path(__file__).parent.parent / "data_source" / "papers"

_session_lock = Lock()
_global_session = None
_arxiv_lock = Lock()
_last_arxiv = [0.0]
ARXIV_DELAY = 3.5  # seconds between arXiv requests


def _session() -> requests.Session:
    global _global_session
    with _session_lock:
        if _global_session is None:
            s = requests.Session()
            s.mount("https://", HTTPAdapter(
                max_retries=Retry(total=5, backoff_factor=1.5,
                                  status_forcelist=[500, 502, 503, 504])
            ))
            s.headers["User-Agent"] = "Mozilla/5.0 (compatible; research-crawler/1.0)"
            _global_session = s
        return _global_session


def _download_from_openreview(forum_id: str, dest: Path) -> bool:
    url = f"https://openreview.net/pdf?id={forum_id}"
    try:
        r = _session().get(url, timeout=60, stream=True)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"):
            dest.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


def _download_from_arxiv(arxiv_id: str, dest: Path) -> bool:
    if not arxiv_id:
        return False
    # Rate-limit arXiv requests
    with _arxiv_lock:
        elapsed = time.time() - _last_arxiv[0]
        if elapsed < ARXIV_DELAY:
            time.sleep(ARXIV_DELAY - elapsed)
        _last_arxiv[0] = time.time()
    url = f"https://arxiv.org/pdf/{arxiv_id}"
    try:
        r = _session().get(url, timeout=60, stream=True, allow_redirects=True)
        if r.status_code == 200:
            dest.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


def download_one(paper_id: str, meta: dict, out_dir: Path, resume: bool) -> tuple[str, str]:
    dest = out_dir / f"{paper_id}.pdf"
    if resume and dest.exists() and dest.stat().st_size > 1024:
        return paper_id, "skipped"

    forum_id = meta.get("forum_id", "")
    arxiv_id = meta.get("arxiv_id", "")

    if forum_id and _download_from_openreview(forum_id, dest):
        return paper_id, "ok:openreview"
    if arxiv_id and _download_from_arxiv(arxiv_id, dest):
        return paper_id, "ok:arxiv"
    return paper_id, "failed"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory for PDFs")
    p.add_argument("--limit", type=int, default=None, help="Download at most N papers")
    p.add_argument("--resume", action="store_true", help="Skip already-downloaded PDFs")
    p.add_argument("--workers", type=int, default=4, help="Parallel download workers")
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not METADATA_FILE.exists():
        print(f"Metadata file not found: {METADATA_FILE}")
        return

    with open(METADATA_FILE) as f:
        metadata: dict = json.load(f)

    papers = list(metadata.items())
    if args.limit:
        papers = papers[: args.limit]

    print(f"Downloading {len(papers)} papers → {out_dir}")
    if args.resume:
        print("Resume mode: skipping existing PDFs")

    results = {"ok:openreview": 0, "ok:arxiv": 0, "skipped": 0, "failed": 0}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(download_one, pid, meta, out_dir, args.resume): pid
            for pid, meta in papers
        }
        with tqdm(total=len(futures), unit="paper") as bar:
            for future in as_completed(futures):
                paper_id, status = future.result()
                results[status] = results.get(status, 0) + 1
                bar.set_postfix(ok=results["ok:openreview"] + results["ok:arxiv"],
                                skip=results["skipped"], fail=results["failed"])
                bar.update(1)

    print("\nSummary:")
    print(f"  OpenReview: {results['ok:openreview']}")
    print(f"  arXiv:      {results['ok:arxiv']}")
    print(f"  Skipped:    {results['skipped']}")
    print(f"  Failed:     {results['failed']}")

    if results["failed"]:
        print("\nFailed paper IDs:")
        # Re-run to collect failed IDs (they're not tracked above for simplicity)
        print("  Run again with --resume to retry failed papers.")


if __name__ == "__main__":
    main()
