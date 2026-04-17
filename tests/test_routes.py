# Step 1: Import FastAPI's test client and the app under test
# TestClient wraps the app in a requests-compatible interface — no server needed
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# Step 2: Test GET /structures returns the expected stub response
def test_get_structures_returns_stub():
    response = client.get("/structures")
    assert response.status_code == 200
    assert response.json() == {"status": "not implemented"}


# Step 3: Test POST /segment returns the expected stub response
def test_post_segment_returns_stub():
    response = client.post("/segment")
    assert response.status_code == 200
    assert response.json() == {"status": "not implemented"}
