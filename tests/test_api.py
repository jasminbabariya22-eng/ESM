import pytest

def test_list_definitions_empty(client):
    response = client.get("/workflow/definitions")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["Error"]["Error"] is False

def test_create_definition_draft(client):
    payload = {
        "spec_id": "ApiTestWorkflow",
        "name": "API Test Process",
        "description": "Validation checks process definition",
        "tags": "test, api"
    }
    response = client.post("/workflow/definitions", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["Error"]["Error"] is False
    assert res_data["data"]["spec_id"] == "ApiTestWorkflow"
