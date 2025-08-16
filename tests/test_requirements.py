def test_requirements_known_code(client):
    r = client.get("/v1/requirements?code=70551")
    assert r.status_code == 200
    data = r.json()
    assert data["requiresAuth"] is True
    assert "Clinical notes" in data["requiredDocs"]

def test_requirements_unknown_code(client):
    r = client.get("/v1/requirements?code=99999")
    assert r.status_code == 200
    data = r.json()
    # adapt to your current behavior; if unknown defaults to False per your latest code:
    assert data["requiresAuth"] is False
    assert data["requiredDocs"] == []
