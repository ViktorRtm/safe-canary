"""Exercise live-traffic rollback; report all client-observed results."""
import json
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from http_client import request_prediction, summary
from route import change_route

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "rollback_proof.json"


def spaced_request(i):
    # Spread requests over the reload interval to sample in-flight traffic.
    time.sleep(i * 0.003)
    return request_prediction()


def image_id():
    return subprocess.check_output(
        ["docker", "image", "inspect", "--format={{.Id}}", "safe-ml-inference:1.0.0"],
        text=True, timeout=10
    ).strip()

def main():
    image_before = image_id()
    with ThreadPoolExecutor(max_workers=24) as executor:
        futures = [executor.submit(spaced_request, i) for i in range(300)]
        time.sleep(0.12)
        change_route(0)   # traffic rollback, no build/restart
        during = [future.result() for future in futures]
    time.sleep(1.0)  # allow old workers / prior connections to drain
    with ThreadPoolExecutor(max_workers=12) as executor:
        after = list(executor.map(lambda _: request_prediction(), range(150)))
    during_summary = summary(during)
    after_summary = summary(after)
    image_after = image_id()
    verified = (
        image_before == image_after and
        during_summary["requests"] == during_summary["success"]
        and during_summary["unique_request_ids"] == during_summary["requests"]
        and after_summary["requests"] == after_summary["success"]
        and after_summary["by_version"]["v2"] == 0
        and after_summary["by_version"]["v1"] == after_summary["requests"]
    )
    report = {"result": "PASS" if verified else "FAIL",
              "rollback_target": "v1",
              "image_id_before": image_before, "image_id_after": image_after,
              "same_image_before_after": image_before == image_after,
              "during_reload": during_summary, "after_reload": after_summary,
              "claim_scope": "Observed requests in this test; not a formal no-downtime SLA guarantee"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not verified:
        raise SystemExit("ROLLBACK_VERIFICATION=FAIL")

if __name__ == "__main__":
    main()
