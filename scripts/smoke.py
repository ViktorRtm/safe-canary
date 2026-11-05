"""Check both backends and public gateway contracts."""
import json
import urllib.request
from http_client import request_prediction


def get(url):
    with urllib.request.urlopen(url, timeout=5) as response:
        assert response.status == 200
        return json.loads(response.read())

def main():
    for port, expected in ((18081, "v1"), (18082, "v2")):
        base = f"http://127.0.0.1:{port}"
        assert get(base + "/ready")["model_version"] == expected
        assert get(base + "/version")["model_version"] == expected
        prediction = request_prediction(base)
        assert prediction["ok"] and prediction["model_version"] == expected
        print(f"BACKEND_SMOKE=PASS version={expected}")
    assert get("http://127.0.0.1:8080/health")["status"] == "ok"
    proxy_prediction = request_prediction()
    assert proxy_prediction["ok"] and proxy_prediction["model_version"] in {"v1", "v2"}
    print("GATEWAY_SMOKE=PASS")

if __name__ == "__main__":
    main()
