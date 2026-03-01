from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
import uuid


_lock = Lock()
_projects: Dict[str, Dict[str, Dict[str, Any]]] = {}
_project_name_index: Dict[Tuple[str, str], str] = {}
_portfolio_items: Dict[str, Dict[str, Dict[str, Any]]] = {}
_selection: Dict[str, Dict[str, Any]] = {}
_project_overrides: Dict[Tuple[str, str], Dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now().isoformat()


def upsert_project(user_id: str, project_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        key = (user_id, project_name)
        project_id = _project_name_index.get(key)
        created_at = now_iso()
        if project_id is None:
            project_id = str(uuid.uuid4())
            _project_name_index[key] = project_id
        existing = _projects.setdefault(user_id, {}).get(project_id, {})
        record = {
            **existing,
            **payload,
            "id": project_id,
            "user_id": user_id,
            "project_name": project_name,
            "created_at": existing.get("created_at", created_at),
        }
        _projects.setdefault(user_id, {})[project_id] = record
        return dict(record)


def list_projects(user_id: str) -> List[Dict[str, Any]]:
    with _lock:
        items = list(_projects.get(user_id, {}).values())
    items.sort(key=lambda x: x.get("scan_timestamp") or "", reverse=True)
    return [dict(i) for i in items]


def get_project(user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        item = _projects.get(user_id, {}).get(project_id)
        return dict(item) if item else None


def delete_project(user_id: str, project_id: str) -> bool:
    with _lock:
        projects = _projects.get(user_id, {})
        item = projects.pop(project_id, None)
        if item is None:
            return False
        _project_name_index.pop((user_id, item.get("project_name", "")), None)
        _project_overrides.pop((user_id, project_id), None)
        return True


def upsert_portfolio_item(user_id: str, payload: Dict[str, Any], item_id: Optional[str] = None) -> Dict[str, Any]:
    with _lock:
        if item_id is None:
            item_id = str(uuid.uuid4())
        existing = _portfolio_items.setdefault(user_id, {}).get(item_id, {})
        now = now_iso()
        record = {
            **existing,
            **payload,
            "id": item_id,
            "user_id": user_id,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }
        _portfolio_items.setdefault(user_id, {})[item_id] = record
        return dict(record)


def list_portfolio_items(user_id: str) -> List[Dict[str, Any]]:
    with _lock:
        return [dict(i) for i in _portfolio_items.get(user_id, {}).values()]


def get_portfolio_item(user_id: str, item_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        item = _portfolio_items.get(user_id, {}).get(item_id)
        return dict(item) if item else None


def delete_portfolio_item(user_id: str, item_id: str) -> bool:
    with _lock:
        return _portfolio_items.get(user_id, {}).pop(item_id, None) is not None


def get_selection(user_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        row = _selection.get(user_id)
        return dict(row) if row else None


def upsert_selection(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        existing = _selection.get(user_id, {})
        now = now_iso()
        row = {
            "user_id": user_id,
            "project_order": payload.get("project_order", existing.get("project_order", [])),
            "skill_order": payload.get("skill_order", existing.get("skill_order", [])),
            "selected_project_ids": payload.get("selected_project_ids", existing.get("selected_project_ids", [])),
            "selected_skill_ids": payload.get("selected_skill_ids", existing.get("selected_skill_ids", [])),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }
        _selection[user_id] = row
        return dict(row)


def delete_selection(user_id: str) -> bool:
    with _lock:
        return _selection.pop(user_id, None) is not None


def get_project_override(user_id: str, project_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        row = _project_overrides.get((user_id, project_id))
        return dict(row) if row else None


def get_project_overrides_for_projects(user_id: str, project_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    with _lock:
        return {
            project_id: dict(_project_overrides[(user_id, project_id)])
            for project_id in project_ids
            if (user_id, project_id) in _project_overrides
        }


def upsert_project_override(user_id: str, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        existing = _project_overrides.get((user_id, project_id), {})
        now = now_iso()
        row = {
            **existing,
            **payload,
            "user_id": user_id,
            "project_id": project_id,
            "created_at": existing.get("created_at", now),
            "updated_at": now,
        }
        _project_overrides[(user_id, project_id)] = row
        return dict(row)


def delete_project_override(user_id: str, project_id: str) -> bool:
    with _lock:
        return _project_overrides.pop((user_id, project_id), None) is not None
