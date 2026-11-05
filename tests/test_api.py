from fastapi.testclient import TestClient

from app.api import app


def test_service_readiness_and_version():
    with TestClient(app) as client:
        assert client.get('/health').json()['status'] == 'ok'
        assert client.get('/ready').status_code == 200
        assert client.get('/version').json()['model_version'] == 'v1'


def test_predict_response_contains_model_version():
    with TestClient(app) as client:
        response = client.post('/predict', json={'x1': 1.0, 'x2': 1.0})
        assert response.status_code == 200
        payload = response.json()
        assert payload['prediction'] == 1
        assert payload['model_version'] == 'v1'
        assert payload['request_id']


def test_invalid_input_is_rejected():
    with TestClient(app) as client:
        response = client.post('/predict', json={'x1': 'wrong', 'x2': 1.0})
        assert response.status_code == 422
