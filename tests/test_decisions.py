from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate import scores
from assess_canary import decide
from route import upstream

def test_metrics():
    assert scores([1, 0, 1], [1, 0, 1])["f1"] == 1.0
    assert scores([1, 0, 1], [0, 0, 0])["recall"] == 0.0

def test_quality_gate_fails_on_ml_regression():
    q = {"v1": {"f1": 0.95, "recall": 0.94},
         "v2": {"f1": 0.20, "recall": 0.10}}
    t = {"requests": 500, "errors": 0, "by_version": {"v1": 475, "v2": 25}, "p95_ms": 10, "by_version_metrics": {"v1": {"error_rate": 0.0, "p95_ms": 9}, "v2": {"error_rate": 0.0, "p95_ms": 10}}}
    decision = decide(q, t)
    assert decision["decision"] == "ROLLBACK"
    assert "RECALL_REGRESSION" in decision["reasons"]

def test_traffic_weights_and_rollback():
    assert "weight=95" in upstream(5)
    assert "weight=5" in upstream(5)
    assert "canary:8000" not in upstream(0)
    assert "stable:8000" not in upstream(100)
