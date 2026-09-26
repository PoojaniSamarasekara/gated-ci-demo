import os

os.environ.setdefault("ADMIN_API_KEY", "test-secret-for-ci")

from fastapi.testclient import TestClient

from app.main import _todos, app

client = TestClient(app)


def setup_function() -> None:
    _todos.clear()


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_list_todo() -> None:
    resp = client.post("/todos", json={"title": "Write CI pipeline"})
    assert resp.status_code == 201
    todo = resp.json()
    assert todo["title"] == "Write CI pipeline"
    assert todo["done"] is False

    resp = client.get("/todos")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_missing_todo_returns_404() -> None:
    resp = client.get("/todos/does-not-exist")
    assert resp.status_code == 404


def test_update_todo() -> None:
    created = client.post("/todos", json={"title": "Draft"}).json()
    resp = client.put(
        f"/todos/{created['id']}", json={"title": "Draft", "done": True}
    )
    assert resp.status_code == 200
    assert resp.json()["done"] is True


def test_delete_todo() -> None:
    created = client.post("/todos", json={"title": "Temp"}).json()
    resp = client.delete(f"/todos/{created['id']}")
    assert resp.status_code == 204
    resp = client.get(f"/todos/{created['id']}")
    assert resp.status_code == 404


def test_admin_bulk_delete_requires_correct_key() -> None:
    client.post("/todos", json={"title": "A"})
    client.post("/todos", json={"title": "B"})

    # Missing or wrong key is rejected
    resp = client.delete("/todos")
    assert resp.status_code == 403

    resp = client.delete("/todos", headers={"X-Admin-Key": "wrong-key"})
    assert resp.status_code == 403

    # Correct key, sourced from the ADMIN_API_KEY secret, is allowed
    correct_key = os.environ["ADMIN_API_KEY"]
    resp = client.delete("/todos", headers={"X-Admin-Key": correct_key})
    assert resp.status_code == 204
    assert client.get("/todos").json() == []
