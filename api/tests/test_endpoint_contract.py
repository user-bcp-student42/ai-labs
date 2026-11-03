from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from test_api import headers, jwt_secret

__all__ = ["jwt_secret"]

MAX_UPLOAD_SIZE = 1024 * 1024


def make_client(tmp_path: Path) -> TestClient:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    return TestClient(app)


class FakeUpstreamResponse:
    def __init__(self, status: int, data: bytes) -> None:
        self.status = status
        self.data = data


class FakePoolManager:
    calls: list[tuple[str, str]] = []
    result: Any = None

    def __init__(self) -> None:
        pass

    def request(self, method: str, url: str, timeout: float) -> FakeUpstreamResponse:
        FakePoolManager.calls.append((method, url))
        if isinstance(FakePoolManager.result, Exception):
            raise FakePoolManager.result
        return FakePoolManager.result


@pytest.fixture
def fake_upstream(monkeypatch: pytest.MonkeyPatch) -> type[FakePoolManager]:
    FakePoolManager.calls = []
    FakePoolManager.result = FakeUpstreamResponse(200, b'{"status":"UP"}')
    monkeypatch.setattr("app.main.urllib3.PoolManager", FakePoolManager)
    return FakePoolManager


# GET /api/tasks

def test_list_returns_empty_array_for_user_without_tasks(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=headers("auditor"))
    assert response.status_code == 200
    assert response.json() == []


def test_list_without_authorization_header_returns_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_list_empty_owner_query_falls_back_to_identity(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/tasks", headers=headers(), params={"owner": ""})
    assert response.status_code == 200
    assert [task["owner"] for task in response.json()] == ["student", "student"]


# POST /api/tasks

def test_create_with_empty_payload_applies_documented_defaults(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=headers(), json={})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == ""
    assert body["description"] == ""
    assert body["status"] == "TODO"
    assert body["priority"] == "MEDIUM"
    assert body["owner"] == "student"


def test_create_without_body_returns_422(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body"]


def test_create_with_non_object_body_returns_422(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", headers=headers(), json=["Refactor login"])
    assert response.status_code == 422


def test_create_without_authorization_header_returns_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/tasks", json={"title": "Sin token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


# GET /api/summary

def test_summary_for_user_without_tasks_is_empty(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/summary", headers=headers("auditor"))
    assert response.status_code == 200
    assert response.json() == {"owner": "auditor", "total": 0, "byStatus": {}, "highPriorityOpen": 0}


def test_summary_excludes_closed_high_priority_tasks(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        for status in ("DONE", "ARCHIVED"):
            client.post("/api/tasks", headers=headers(), json={"title": status, "status": status, "priority": "HIGH"})
        response = client.get("/api/summary", headers=headers())
    assert response.json()["total"] == 4
    assert response.json()["highPriorityOpen"] == 1


def test_summary_without_authorization_header_returns_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/summary")
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


# POST /api/requirements

def test_upload_file_at_exact_size_limit_is_accepted(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("limite.txt", b"a" * MAX_UPLOAD_SIZE, "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == MAX_UPLOAD_SIZE


def test_upload_empty_file_is_stored_with_zero_size(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("vacio.txt", b"", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == 0


def test_upload_file_without_extension_returns_422(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requisitos", b"sin extension", "text/plain")},
        )
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid file name or extension"}


def test_upload_name_with_disallowed_characters_returns_422(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("a$b.txt", b"x", "text/plain")},
        )
    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid file name or extension"}


def test_upload_name_longer_than_limit_returns_422(tmp_path: Path) -> None:
    long_name = "a" * 125 + ".txt"
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": (long_name, b"x", "text/plain")},
        )
    assert response.status_code == 422


def test_upload_without_file_field_returns_422(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post("/api/requirements", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_upload_without_authorization_header_returns_401(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/requirements",
            files={"file": ("requisitos.txt", b"x", "text/plain")},
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


# GET /api/backend-health

def test_backend_health_returns_upstream_status_and_body(tmp_path: Path, fake_upstream: type[FakePoolManager]) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 200, "body": '{"status":"UP"}'}


def test_backend_health_uses_configured_url(tmp_path: Path, fake_upstream: type[FakePoolManager], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://auth.test/q/health")
    with make_client(tmp_path) as client:
        client.get("/api/backend-health", headers=headers())
    assert fake_upstream.calls == [("GET", "http://auth.test/q/health")]


def test_backend_health_passes_through_upstream_error_status(tmp_path: Path, fake_upstream: type[FakePoolManager]) -> None:
    fake_upstream.result = FakeUpstreamResponse(503, b'{"status":"DOWN"}')
    with make_client(tmp_path) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json()["status"] == 503


def test_backend_health_unreachable_upstream_returns_status_zero(tmp_path: Path, fake_upstream: type[FakePoolManager]) -> None:
    fake_upstream.result = OSError("connection refused")
    with make_client(tmp_path) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {"requestedBy": "student", "status": 0, "body": "connection refused"}


def test_backend_health_without_authorization_header_returns_401(tmp_path: Path, fake_upstream: type[FakePoolManager]) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/backend-health")
    assert response.status_code == 401
    assert fake_upstream.calls == []
