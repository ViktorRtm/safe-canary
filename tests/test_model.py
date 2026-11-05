from pathlib import Path

from app.model import Model

ROOT = Path(__file__).resolve().parents[1]

def test_stable_and_canary_are_distinct():
    stable = Model(str(ROOT / "models/v1.json"), "v1")
    canary = Model(str(ROOT / "models/v2.json"), "v2")
    assert stable.predict(2.0, 1.0)[0] == 1
    assert canary.predict(2.0, 1.0)[0] == 0
    assert stable.predict(-2.0, -1.0)[0] == 0

def test_schema_and_version_validation():
    import pytest
    with pytest.raises(ValueError, match="Model version"):
        Model(str(ROOT / "models/v1.json"), "v2")
