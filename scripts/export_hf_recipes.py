#!/usr/bin/env python3
"""Export text-only Food.com recipes from Hugging Face's dataset viewer API.

No image bytes, signed URLs, or heavy Hugging Face libraries are downloaded.
Usage: python scripts/export_hf_recipes.py --limit 15698
"""
import argparse
import concurrent.futures
import gzip
import json
import math
import random
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
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
    for attempt in range(6):
        try:
            with urlopen(Request(url, headers={"User-Agent": "REFOOD-recipe-text-export/1.0",
                                                "Accept": "application/json"}), timeout=45) as f:
                data = json.load(f)
            if data.get("partial"):
                raise RuntimeError("Hugging Face reports a partial dataset")
            return data
        except (HTTPError, URLError, TimeoutError, ValueError) as e:
            if attempt == 5:
                raise RuntimeError(f"Could not fetch offset {offset}") from e
            time.sleep(min(30, 1.5 * 2 ** attempt) + random.random())


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
    parser.add_argument("--limit", type=int, default=15698, help="Maximum number of rows to fetch")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", default="dist/refood-recipes.jsonl.gz")
    args = parser.parse_args()
    if args.limit < 1 or args.workers not in range(1, 9):
        parser.error("limit must be positive and workers 1-8")
    first = fetch_page(0, min(100, args.limit))
    total = min(args.limit, first.get("num_rows_total") or args.limit)
    offsets = list(range(0, total, 100))
    def get(offset):
        return offset, first if offset == 0 else fetch_page(offset, min(100, total - offset))
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = dropped = 0
    # Ordered map avoids non-deterministic output while requests happen concurrently.
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        with gzip.open(path, "wt", encoding="utf-8", compresslevel=6) as output:
            for i, (offset, page) in enumerate(pool.map(get, offsets), 1):
                rows = page.get("rows", [])
                expected = min(100, total - offset)
                if len(rows) != expected:
                    raise RuntimeError(f"Offset {offset}: expected {expected} records, received {len(rows)}")
                for row in rows:
                    recipe = extract(row, row.get("row_idx", offset))
                    if recipe:
                        output.write(json.dumps(recipe, ensure_ascii=False, separators=(",", ":")) + "\n")
                        kept += 1
                    else:
                        dropped += 1
                if i % 10 == 0 or i == len(offsets):
                    print(f"Fetched {min(offset+len(rows), total)}/{total}, kept={kept}, skipped={dropped}", flush=True)
    print(json.dumps({"dataset": DATASET, "fetched": total, "kept": kept,
                      "skipped": dropped, "file": str(path),
                      "compressed_bytes": path.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
