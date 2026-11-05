"""Generate labelled synthetic cases; *only* for the educational demo."""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "labelled.jsonl"

def main():
    rng = random.Random(2026)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as handle:
        for case in range(1000):
            x1 = round(rng.uniform(-3, 3), 5)
            x2 = round(rng.uniform(-3, 3), 5)
            # The labels reflect the intended task; v2 deliberately violates it.
            y = int(x1 + x2 >= 0)
            handle.write(json.dumps({"case_id": case, "x1": x1, "x2": x2, "label": y}) + "\n")
    print(f"FIXTURE_CREATED rows=1000 path={OUT}")

if __name__ == "__main__":
    main()
