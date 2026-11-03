from __future__ import annotations

import sqlite3
from typing import Any


def find_tasks_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id,title,description,status,owner,priority,created_at FROM tasks WHERE owner = ? ORDER BY id",
        (owner,),
    ).fetchall()


def insert_task(connection: sqlite3.Connection, values: dict[str, Any]) -> int:
    cursor = connection.execute(
        "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))",
        (values["title"], values["description"], values["status"], values["owner"], values["priority"]),
    )
    connection.commit()
    return int(cursor.lastrowid or 0)


def find_task_by_id(connection: sqlite3.Connection, task_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id,title,description,status,owner,priority,created_at FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()


def find_status_and_priority_by_owner(connection: sqlite3.Connection, owner: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT status,priority FROM tasks WHERE owner = ?",
        (owner,),
    ).fetchall()
