"""Toy two-feature binary classifiers, stored as immutable, versioned JSON artifacts.

This is an educational model for demonstrating release safety, not a fraud model.
"""
import json
import math
from pathlib import Path


class Model:
    def __init__(self, path: str, required_version: str):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload["version"] != required_version:
            raise ValueError("Model version does not match MODEL_VERSION")
        if payload["schema_version"] != "features-v1" or payload["features"] != ["x1", "x2"]:
            raise ValueError("Incompatible model/feature contract")
        weights = payload["weights"]
        if len(weights) != 2 or not all(math.isfinite(float(w)) for w in weights):
            raise ValueError("Invalid model weights")
        self.version = required_version
        self.weights = tuple(float(w) for w in weights)
        self.bias = float(payload["bias"])

    def predict(self, x1: float, x2: float):
        score = self.weights[0] * x1 + self.weights[1] * x2 + self.bias
        score = max(-40.0, min(40.0, score))
        probability = 1.0 / (1.0 + math.exp(-score))
        return int(probability >= 0.5), probability
