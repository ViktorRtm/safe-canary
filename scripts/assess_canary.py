"""A fail-closed decision gate: don't promote on missing or insufficient signals."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def decide(quality, traffic):
    stable = quality["v1"]
    canary = quality["v2"]
    total = traffic["requests"]
    canary_observed = traffic["by_version"]["v2"]
    reasons = []
    # For the educational fixture the expected share is approximately 5%.
    if canary_observed < 10:
        reasons.append("INSUFFICIENT_CANARY_SAMPLE")
    if traffic["errors"] > max(0, int(total * 0.01)):
        reasons.append("ERROR_RATE_HIGH")
    v2_technical = traffic.get("by_version_metrics", {}).get("v2", {})
    if v2_technical.get("error_rate") is None or v2_technical["error_rate"] > 0.01:
        reasons.append("CANARY_ERROR_RATE_HIGH_OR_MISSING")
    if v2_technical.get("p95_ms") is None or v2_technical["p95_ms"] > 250:
        reasons.append("CANARY_LATENCY_P95_HIGH_OR_MISSING")
    if canary["recall"] < stable["recall"] - 0.05:
        reasons.append("RECALL_REGRESSION")
    if canary["f1"] < stable["f1"] - 0.05:
        reasons.append("F1_REGRESSION")
    return {"decision": "ROLLBACK" if reasons else "PROMOTE_ELIGIBLE",
            "reasons": reasons, "thresholds": {"error_rate_max": .01,
            "latency_p95_max_ms": 250, "recall_drop_max": .05,
            "f1_drop_max": .05, "min_canary_requests": 10},
            "observed_traffic": traffic, "offline_quality": quality,
            "note": "Offline labels are synthetic. In real deployment delay promotion until reliable labels arrive."}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-rejection", action="store_true",
                        help="For teaching only: assert that the intentionally faulty v2 gets blocked")
    args = parser.parse_args()
    quality = json.loads((ROOT / "reports" / "quality.json").read_text(encoding="utf-8"))
    traffic = json.loads((ROOT / "reports" / "canary_traffic.json").read_text(encoding="utf-8"))
    result = decide(quality, traffic)
    out = ROOT / "reports" / "canary_assessment.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.expect_rejection:
        if result["decision"] != "ROLLBACK" or not any(
            item in result["reasons"] for item in ("RECALL_REGRESSION", "F1_REGRESSION")
        ):
            raise SystemExit("UNEXPECTED_DECISION: expected an ML quality rollback")
    elif result["decision"] != "PROMOTE_ELIGIBLE":
        raise SystemExit("QUALITY_GATE=FAIL — version must NOT be promoted")

if __name__ == "__main__":
    main()
