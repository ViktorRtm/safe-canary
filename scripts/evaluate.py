"""Evaluate both versioned model artifacts on identical labelled data."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.model import Model  # noqa: E402

DATA = ROOT / "data" / "labelled.jsonl"
OUT = ROOT / "reports" / "quality.json"


def scores(true, pred):
    tp = sum(a == 1 and b == 1 for a, b in zip(true, pred))
    tn = sum(a == 0 and b == 0 for a, b in zip(true, pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(true, pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(true, pred))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 5), "recall": round(r, 5),
            "f1": round(f1, 5), "tp": tp, "tn": tn, "fp": fp, "fn": fn}


def main():
    if not DATA.exists():
        raise SystemExit("First run: python scripts/generate_fixture.py")
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()]
    truth = [r["label"] for r in rows]
    results = {"samples": len(rows), "source": "synthetic_labelled_fixture"}
    for version in ("v1", "v2"):
        model = Model(str(ROOT / "models" / f"{version}.json"), version)
        pred = [model.predict(row["x1"], row["x2"])[0] for row in rows]
        results[version] = scores(truth, pred)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
