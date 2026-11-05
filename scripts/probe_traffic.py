"""Sample routed requests; compare observed version mix to requested weights."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from http_client import request_prediction, summary

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", default="reports/canary_traffic.json")
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    if args.requests <= 0 or args.workers <= 0:
        raise SystemExit("--requests and --workers must be positive")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = list(executor.map(lambda _: request_prediction(args.url), range(args.requests)))
    result = summary(rows)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit("HTTP_ERRORS=FAIL")

if __name__ == "__main__":
    main()
