from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_swagger import patch_fastapi


def test_app():
    app = FastAPI(title="Test App", docs_url=None, swagger_ui_oauth2_redirect_url=None)
    patch_fastapi(app, title="Test App")
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
