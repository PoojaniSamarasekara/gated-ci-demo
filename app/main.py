"""
Tiny Todo API used as the vehicle for the Gated CI Pipeline activity.

The app itself is intentionally trivial. The one interesting piece is
`delete_all_todos`, which requires an admin key pulled from an
environment variable (ADMIN_API_KEY). That gives this repo a real
secret to manage in CI, instead of a fake one bolted on for show.
"""

from __future__ import annotations

import os
import uuid

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Todo API")

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")


class Todo(BaseModel):
    title: str
    done: bool = False


class TodoOut(Todo):
    id: str


_todos: dict[str, TodoOut] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/todos", response_model=list[TodoOut])
def list_todos() -> list[TodoOut]:
    return list(_todos.values())


@app.post("/todos", response_model=TodoOut, status_code=201)
def create_todo(todo: Todo) -> TodoOut:
    todo_id = str(uuid.uuid4())
    out = TodoOut(id=todo_id, **todo.model_dump())
    _todos[todo_id] = out
    return out


@app.get("/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: str) -> TodoOut:
    if todo_id not in _todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return _todos[todo_id]


@app.put("/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: str, todo: Todo) -> TodoOut:
    if todo_id not in _todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    out = TodoOut(id=todo_id, **todo.model_dump())
    _todos[todo_id] = out
    return out


@app.delete("/todos/{todo_id}", status_code=204, response_model=None)
def delete_todo(todo_id: str) -> None:
    if todo_id not in _todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    del _todos[todo_id]


@app.delete("/todos", status_code=204, response_model=None)
def delete_all_todos(x_admin_key: str | None = Header(default=None)) -> None:
    """Admin-only bulk delete. Requires the ADMIN_API_KEY secret.

    This is the endpoint that gives the project a genuine reason to
    hold a secret: without the right X-Admin-Key header, the wipe is
    refused, exactly like the activity wants (5.5 Secrets Management).
    """
    if not ADMIN_API_KEY or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    _todos.clear()
