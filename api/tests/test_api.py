import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

TEST_JWT_SECRET = "test-only-secret"


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSHOP_JWT_SECRET", TEST_JWT_SECRET)


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def sign_jwt(header: dict[str, str], claims: dict[str, object], secret: str = TEST_JWT_SECRET) -> str:
    encoded_header = b64url(json.dumps(header).encode())
    encoded_claims = b64url(json.dumps(claims).encode())
    signing_input = f"{encoded_header}.{encoded_claims}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_claims}.{b64url(signature)}"


def token(username: str = "student", role: str = "STUDENT", expires_at: int | None = None, secret: str = TEST_JWT_SECRET) -> str:
    claims = {
        "sub": username,
        "role": role,
        "exp": expires_at if expires_at is not None else int(time.time()) + 3600,
        "iss": "ai-labs-auth",
        "aud": "ai-labs-api",
    }
    return sign_jwt({"alg": "HS256", "typ": "JWT"}, claims, secret)


def headers(username: str = "student", role: str = "STUDENT") -> dict[str, str]:
    return {"Authorization": f"Bearer {token(username, role)}"}


def test_rejects_legacy_token_without_signature(tmp_path: Path) -> None:
    legacy = base64.b64encode(f"student|STUDENT|{int(time.time()) + 3600}|WORKSHOP_SECRET_2026".encode()).decode()
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {legacy}"})
    assert response.status_code == 401


def test_rejects_token_signed_with_other_secret(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token(secret='forged')}"})
    assert response.status_code == 401


def test_rejects_expired_signed_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token(expires_at=int(time.time()) - 10)}"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("expires_at", "expected_status"),
    [(1_700_000_000 - 1, 401), (1_700_000_000, 401), (1_700_000_000 + 1, 200)],
)
def test_token_expiration_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expires_at: int,
    expected_status: int,
) -> None:
    current_time = 1_700_000_000
    monkeypatch.setattr("app.security.time.time", lambda: current_time)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token(expires_at=expires_at)}"},
        )
    assert response.status_code == expected_status


@pytest.mark.parametrize("expires_at", ["soon", None, [1]])
def test_rejects_non_numeric_expiration_with_generic_401(tmp_path: Path, expires_at: object) -> None:
    claims = {"sub": "student", "role": "STUDENT", "exp": expires_at, "iss": "ai-labs-auth", "aud": "ai-labs-api"}
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {sign_jwt({'alg': 'HS256', 'typ': 'JWT'}, claims)}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


def test_rejects_unexpected_issuer_or_audience(tmp_path: Path) -> None:
    claims = {"sub": "student", "role": "STUDENT", "exp": int(time.time()) + 3600, "iss": "other", "aud": "ai-labs-api"}
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {sign_jwt({'alg': 'HS256', 'typ': 'JWT'}, claims)}"},
        )
    assert response.status_code == 401


def test_rejects_unsupported_algorithm(tmp_path: Path) -> None:
    claims = {"sub": "student", "role": "STUDENT", "exp": int(time.time()) + 3600, "iss": "ai-labs-auth", "aud": "ai-labs-api"}
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get(
            "/api/tasks",
            headers={"Authorization": f"Bearer {sign_jwt({'alg': 'none', 'typ': 'JWT'}, claims)}"},
        )
    assert response.status_code == 401


def test_rejects_token_when_secret_not_configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKSHOP_JWT_SECRET")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {token()}"})
    assert response.status_code == 401


def test_accepts_signed_token_and_uses_subject_as_identity(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers={"Authorization": f"Bearer {token(username='maria')}"},
            json={"title": "Signed identity"},
        )
    assert response.status_code == 201
    assert response.json()["owner"] == "maria"


def test_characterizes_expired_legacy_token_rejected(tmp_path: Path) -> None:
    raw = f"student|STUDENT|{int(time.time()) - 10}|WORKSHOP_SECRET_2026"
    expired = base64.b64encode(raw.encode()).decode()
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_characterizes_wrong_fourth_field_rejected(tmp_path: Path) -> None:
    raw = f"student|STUDENT|{int(time.time()) + 3600}|OTHER_SECRET"
    wrong = base64.b64encode(raw.encode()).decode()
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Bearer {wrong}"})
    assert response.status_code == 401


def test_characterizes_non_bearer_scheme_rejected(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": f"Basic {token()}"})
    assert response.status_code == 401


def test_characterizes_invalid_base64_rejected(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer !!!not-base64!!!"})
    assert response.status_code == 401


def test_lists_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_creates_task_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        created = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Add tests", "description": "Improve coverage", "status": "TODO", "priority": "HIGH"},
        )
        summary = client.get("/api/summary", headers=headers())
    assert created.status_code == 201
    assert created.json()["owner"] == "student"
    assert summary.json()["total"] == 3


def test_uploads_requirement(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Login must be accessible", "text/plain")},
        )
    assert response.status_code == 201
    assert Path(response.json()["storedAt"]).exists()


def test_upload_storage_is_isolated_and_rejects_same_user_duplicate(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        student_upload = client.post(
            "/api/requirements",
            headers=headers("student"),
            files={"file": ("shared.txt", b"student content", "text/plain")},
        )
        trainer_upload = client.post(
            "/api/requirements",
            headers=headers("trainer"),
            files={"file": ("shared.txt", b"trainer content", "text/plain")},
        )
        duplicate_upload = client.post(
            "/api/requirements",
            headers=headers("student"),
            files={"file": ("shared.txt", b"replacement content", "text/plain")},
        )

    assert student_upload.status_code == 201
    assert trainer_upload.status_code == 201
    assert set(student_upload.json()) == {"owner", "fileName", "storedAt", "size"}
    assert student_upload.json()["owner"] == "student"
    assert trainer_upload.json()["owner"] == "trainer"
    student_path = Path(student_upload.json()["storedAt"])
    trainer_path = Path(trainer_upload.json()["storedAt"])
    assert student_path != trainer_path
    assert student_path.read_bytes() == b"student content"
    assert trainer_path.read_bytes() == b"trainer content"
    assert duplicate_upload.status_code == 409
    assert duplicate_upload.json() == {"detail": "File already exists"}
    assert student_path.read_bytes() == b"student content"


def test_stores_traversal_name_only_inside_uploads(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("../escaped.txt", b"traversal probe", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["fileName"] == "escaped.txt"
    stored_path = Path(response.json()["storedAt"])
    assert stored_path.name == "escaped.txt"
    assert upload_dir.resolve() in stored_path.resolve().parents
    assert not (tmp_path / "escaped.txt").exists()


def test_accepts_file_name_with_spaces(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("informe final.txt", b"requisitos", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["fileName"] == "informe final.txt"
    assert Path(response.json()["storedAt"]).exists()


def test_rejects_disallowed_extension(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("payload.exe", b"MZ", "application/octet-stream")},
        )
    assert response.status_code == 422


def test_rejects_file_over_size_limit(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    oversized = b"a" * (1024 * 1024 + 1)
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("big.txt", oversized, "text/plain")},
        )
    assert response.status_code == 413
    assert not (upload_dir / "big.txt").exists()


def test_rejects_invalid_token(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_characterizes_task_payload_shape(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Plain title", "description": "Plain text", "status": "TODO", "priority": "HIGH"},
        )
    assert response.status_code == 201
    assert set(response.json()) == {"id", "title", "description", "status", "owner", "priority", "createdAt"}
    assert response.json()["owner"] == "student"


def test_characterizes_summary_breakdown(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        summary = client.get("/api/summary", headers=headers())
    assert summary.status_code == 200
    assert summary.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_sql_injection_payload_is_stored_as_literal_text(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    payload_title = "x'); DROP TABLE tasks; --"
    with TestClient(app) as client:
        created = client.post("/api/tasks", headers=headers(), json={"title": payload_title, "description": "d"})
        listed = client.get("/api/tasks", headers=headers())
        injected_owner = client.get("/api/tasks", headers=headers(), params={"owner": "' OR '1'='1"})
    assert created.status_code == 201
    assert created.json()["title"] == payload_title
    assert any(task["title"] == payload_title for task in listed.json())
    assert injected_owner.status_code == 403


def test_rejects_other_owner_listing(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        listed = client.get("/api/tasks", headers=headers(), params={"owner": "trainer"})
        summary = client.get("/api/summary", headers=headers(), params={"owner": "trainer"})
    assert listed.status_code == 403
    assert summary.status_code == 403


def test_accepts_own_owner_and_defaults_to_identity(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        own = client.get("/api/tasks", headers=headers(), params={"owner": "student"})
        default = client.get("/api/tasks", headers=headers())
    assert own.status_code == 200
    assert [task["owner"] for task in own.json()] == ["student", "student"]
    assert default.json() == own.json()


def test_rejects_other_owner_creation_and_keeps_identity(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        rejected = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Impersonated", "description": "d", "owner": "trainer"},
        )
        accepted = client.post(
            "/api/tasks",
            headers=headers(),
            json={"title": "Mine", "description": "d", "owner": "student"},
        )
    assert rejected.status_code == 403
    assert accepted.status_code == 201
    assert accepted.json()["owner"] == "student"
