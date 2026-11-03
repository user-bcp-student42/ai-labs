from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

import urllib3
from fastapi import Body, Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.repository import find_status_and_priority_by_owner, find_task_by_id, find_tasks_by_owner, insert_task
from app.security import InvalidTokenError, identity_from_authorization
from app.uploads import InvalidUploadError, UploadTooLargeError, read_bounded, safe_file_name


PRIORITY_HIGH = "HIGH"
CLOSED_STATUSES = frozenset({"DONE", "ARCHIVED"})


def is_high_priority_open(row: sqlite3.Row) -> bool:
    return row["priority"] == PRIORITY_HIGH and row["status"] not in CLOSED_STATUSES


def build_summary(owner: str, rows: list[sqlite3.Row]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    return {
        "owner": owner,
        "total": len(rows),
        "byStatus": by_status,
        "highPriorityOpen": sum(1 for row in rows if is_high_priority_open(row)),
    }


def require_identity(authorization: str = Header(default="")) -> dict[str, str]:
    try:
        return identity_from_authorization(authorization)
    except InvalidTokenError as error:
        raise HTTPException(status_code=401, detail="Invalid token") from error


def authorized_owner(requested_owner: str | None, identity: dict[str, str]) -> str:
    username = identity["username"]
    if not requested_owner or requested_owner == username:
        return username
    raise HTTPException(status_code=403, detail="Forbidden")


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    Path(selected_uploads).mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(selected_db, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL)")
    count = connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
    if count == 0:
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Refactor login','Separar responsabilidades en frontend','TODO','student','HIGH',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Review API','Revisar seguridad de endpoints','IN_PROGRESS','student','MEDIUM',datetime('now'))")
        connection.execute("INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES ('Trainer notes','Preparar retrospectiva','TODO','trainer','LOW',datetime('now'))")
        connection.commit()

    app = FastAPI(title="Workshop Requirements API", version="0.1.0")
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def as_task(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "status": row["status"],
            "owner": row["owner"],
            "priority": row["priority"],
            "createdAt": row["created_at"],
        }

    @app.get("/api/tasks")
    def list_tasks(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(require_identity)) -> list[dict[str, Any]]:
        requested_owner = authorized_owner(owner, identity)
        rows = find_tasks_by_owner(connection, requested_owner)
        return [as_task(row) for row in rows]

    @app.post("/api/tasks", status_code=201)
    def create_task(payload: dict[str, Any] = Body(...), identity: dict[str, str] = Depends(require_identity)) -> dict[str, Any]:
        title = str(payload.get("title", ""))
        description = str(payload.get("description", ""))
        status = str(payload.get("status", "TODO"))
        priority = str(payload.get("priority", "MEDIUM"))
        requested = payload.get("owner")
        owner = authorized_owner(None if requested is None else str(requested), identity)
        values = {"title": title, "description": description, "status": status, "owner": owner, "priority": priority}
        task_id = insert_task(connection, values)
        return as_task(find_task_by_id(connection, task_id))

    @app.get("/api/summary")
    def summary(owner: str | None = Query(default=None), identity: dict[str, str] = Depends(require_identity)) -> dict[str, Any]:
        requested_owner = authorized_owner(owner, identity)
        rows = find_status_and_priority_by_owner(connection, requested_owner)
        return build_summary(requested_owner, rows)

    @app.post("/api/requirements", status_code=201)
    async def upload_requirement(file: UploadFile = File(...), identity: dict[str, str] = Depends(require_identity)) -> dict[str, Any]:
        file_name = safe_file_name(file.filename)
        content = await read_bounded(file)
        target = Path(selected_uploads) / file_name
        target.write_bytes(content)
        return {"owner": identity["username"], "fileName": file_name, "storedAt": str(target), "size": len(content)}

    @app.exception_handler(InvalidUploadError)
    def invalid_upload(_request: Request, _error: InvalidUploadError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "Invalid file name or extension"})

    @app.exception_handler(UploadTooLargeError)
    def upload_too_large(_request: Request, _error: UploadTooLargeError) -> JSONResponse:
        return JSONResponse(status_code=413, content={"detail": "File too large"})

    @app.get("/api/backend-health")
    def backend_health(identity: dict[str, str] = Depends(require_identity)) -> dict[str, Any]:
        url = os.getenv("AUTH_HEALTH_URL", "http://localhost:8080/q/health")
        try:
            response = urllib3.PoolManager().request("GET", url, timeout=3.0)
            return {"requestedBy": identity["username"], "status": response.status, "body": response.data.decode("utf-8")}
        except Exception as error:
            return {"requestedBy": identity["username"], "status": 0, "body": str(error)}

    @app.on_event("shutdown")
    def close_connection() -> None:
        connection.close()

    return app


app = create_app()
