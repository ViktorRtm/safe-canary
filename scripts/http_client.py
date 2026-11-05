"""Small helper shared by smoke, traffic sampling and rollback tests."""
import json
import time
import urllib.error
import urllib.request

BODY = json.dumps({"x1": 1.8, "x2": 0.4}).encode()


def request_prediction(base: str = "http://127.0.0.1:8080"):
    started = time.perf_counter()
    request = urllib.request.Request(
        base + "/predict", data=BODY, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5.0) as response:
            body = json.loads(response.read())
            elapsed = (time.perf_counter() - started) * 1000
            return {"ok": response.status == 200, "status": response.status,
                    "model_version": body.get("model_version"),
                    "request_id": body.get("request_id"), "latency_ms": elapsed}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"ok": False, "status": 0, "model_version": None,
                "request_id": None, "latency_ms": (time.perf_counter() - started) * 1000,
                "error_type": type(exc).__name__}


def summary(rows):
    times = sorted(r["latency_ms"] for r in rows)
    def percentile(p):
        return round(times[min(len(times) - 1, int((len(times) - 1) * p))], 2) if times else None
    by_version = {v: sum(row["model_version"] == v for row in rows) for v in ("v1", "v2")}
    per_version = {}
    for version in ("v1", "v2"):
        subset = [r for r in rows if r["model_version"] == version]
        sample_times = sorted(r["latency_ms"] for r in subset)
        per_version[version] = {
            "requests": len(subset),
            "errors": sum(not r["ok"] for r in subset),
            "p95_ms": round(sample_times[min(len(sample_times)-1, int((len(sample_times)-1)*.95))], 2) if sample_times else None,
            "error_rate": round(sum(not r["ok"] for r in subset) / len(subset), 5) if subset else None,
        }
    return {"requests": len(rows), "success": sum(row["ok"] for row in rows),
            "errors": sum(not row["ok"] for row in rows),
            "by_version": by_version, "by_version_metrics": per_version, "p50_ms": percentile(.50),
            "p95_ms": percentile(.95), "p99_ms": percentile(.99),
            "unique_request_ids": len({r["request_id"] for r in rows if r["request_id"]}),
            "model_version_missing": sum(not r["model_version"] for r in rows),
            "error_rate": round(sum(not r["ok"] for r in rows) / len(rows), 5) if rows else None}
