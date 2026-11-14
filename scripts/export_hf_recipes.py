#!/usr/bin/env python3
"""Export text-only Food.com recipes from Hugging Face's dataset viewer API.

No image bytes, signed URLs, or heavy Hugging Face libraries are downloaded.
Usage: python scripts/export_hf_recipes.py --limit 15698
"""
import argparse
import gzip
import json
import random
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://datasets-server.huggingface.co/rows"
DATASET = "rahul7star/food-recipes"
FIELDS = ("recipe_id", "name", "minutes", "description", "tags",
          "steps", "n_steps", "n_ingredients", "nutrition", "rating", "num_ratings")


def fetch_page(offset, length):
    url = BASE + "?" + urlencode({
        "dataset": DATASET, "config": "default", "split": "train",
        "offset": offset, "length": length,
    })
    for attempt in range(15):
        try:
            with urlopen(Request(url, headers={"User-Agent": "REFOOD-recipe-text-export/1.0",
                                                "Accept": "application/json"}), timeout=45) as f:
                data = json.load(f)
            if data.get("partial"):
                raise RuntimeError("Hugging Face reports a partial dataset")
            return data
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 14:
                raise RuntimeError(f"Could not fetch offset {offset}: HTTP {exc.code}") from exc
            wait = min(120, 5 * (2 ** min(attempt, 5)))
            retry = exc.headers.get("Retry-After")
            if retry:
                try:
                    wait = max(wait, int(retry))
                except ValueError:
                    try:
                        wait = max(wait, (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds())
                    except (TypeError, ValueError):
                        pass
            print(f"Rate limited at offset {offset}; retrying after {wait:.0f}s", flush=True)
            time.sleep(wait + random.random())
        except (URLError, TimeoutError, ValueError) as exc:
            if attempt == 14:
                raise RuntimeError(f"Could not fetch offset {offset}") from exc
            time.sleep(min(90, 3 * 2 ** min(attempt, 5)) + random.random())


def extract(row, row_idx):
    raw = row.get("row") or {}
    entry = {key: raw.get(key) for key in FIELDS}
    markdown = raw.get("markdown") or ""
    match = re.search(r"^## Ingredients\s*\n(.*?)(?=^## |\Z)", markdown, re.M | re.S)
    if not match:
        return None
    ingredients = [x.strip() for x in match.group(1).strip().split(",") if x.strip()]
    if (not ingredients or not entry["name"] or entry["recipe_id"] is None
            or (isinstance(entry["n_ingredients"], int) and len(ingredients) != entry["n_ingredients"])):
        return None
    entry["ingredients"] = ingredients
    entry["source_dataset"] = DATASET
    entry["source_row_idx"] = row_idx
    return entry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15698, help="Maximum total source rows to consider")
    parser.add_argument("--start-offset", type=int, default=0, help="Resume by downloading a separate shard starting at this source row")
    parser.add_argument("--workers", type=int, default=1, help="Compatibility option; always uses sequential requests to avoid HTTP 429")
    parser.add_argument("--delay", type=float, default=2.5, help="Pause in seconds between API requests")
    parser.add_argument("--out", default="dist/refood-recipes.jsonl.gz")
    args = parser.parse_args()
    if args.limit < 1 or args.start_offset < 0 or args.start_offset % 100 or args.workers not in range(1, 9) or args.delay < 0:
        parser.error("Invalid limit/start-offset/workers/delay; start-offset must be a multiple of 100")
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = dropped = completed = 0
    total = args.limit
    error = None
    # A valid gzip file is retained even if a later request fails.
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as output:
        for offset in range(args.start_offset, total, 100):
            try:
                page = fetch_page(offset, min(100, total-offset))
                if offset == args.start_offset:
                    total = min(total, page.get("num_rows_total") or total)
                rows = page.get("rows", [])
                if len(rows) != min(100, total-offset):
                    raise RuntimeError(f"Offset {offset}: incomplete page ({len(rows)} rows)")
                for row in rows:
                    recipe = extract(row, row.get("row_idx", offset))
                    if recipe:
                        output.write(json.dumps(recipe, ensure_ascii=False, separators=(",", ":")) + "\n")
                        kept += 1
                    else:
                        dropped += 1
                completed = offset + len(rows)
                if completed % 1000 == 0 or completed == total:
                    print(f"Fetched {completed}/{total}, kept={kept}, skipped={dropped}", flush=True)
                if completed < total:
                    time.sleep(args.delay)
            except Exception as exc:
                error = exc
                print(f"Export interrupted at offset {offset}: {exc}. Partial gzip is saved.", flush=True)
                break
    print(json.dumps({"dataset": DATASET, "start_offset": args.start_offset,
                      "completed_until_offset": completed, "target_total": total,
                      "kept": kept, "skipped": dropped, "file": str(path),
                      "compressed_bytes": path.stat().st_size,
                      "complete": error is None and completed >= total}, indent=2))
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
