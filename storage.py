import os, json, threading
from typing import Any, Dict, Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import Base, ConfigKV, Site, Schedule, model_to_json_str, json_str_to_model

DB_JSON_PATH = os.getenv("DB_JSON_PATH", "./data/db.json")
DB_URL = os.getenv("DB_URL", "sqlite:///data/app.db")

# ============== JSON 存取（公告/作業/資源/相簿/班規/使用者） ==============
_lock = threading.RLock()
if not os.path.exists(os.path.dirname(DB_JSON_PATH) or "."):
    os.makedirs(os.path.dirname(DB_JSON_PATH) or ".", exist_ok=True)
if not os.path.exists(DB_JSON_PATH):
    with open(DB_JSON_PATH, "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "site": {},         # 將不再使用 JSON 的 site/schedule，保留舊資料兼容
            "schedule": {},
            "announcements": [],
            "assignments": [],
            "resources": [],
            "gallery": [],
            "rules": [],
            "users": []
        }, ensure_ascii=False, indent=2))

def _read() -> Dict[str, Any]:
    with _lock:
        try:
            with open(DB_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
def _write(data: Dict[str, Any]):
    with _lock:
        with open(DB_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def get_(key: str):
    d = _read()
    return d.get(key)

def set_(key: str, value: Any):
    d = _read()
    d[key] = value
    _write(d)
    return value

# ============== SQLAlchemy（設定存 DB） ==============
if not os.path.exists(os.path.dirname(DB_URL.replace("sqlite:///", "")) or "."):
    os.makedirs(os.path.dirname(DB_URL.replace("sqlite:///", "")) or ".", exist_ok=True)

engine = create_engine(DB_URL, future=True)
with engine.begin() as conn:
    Base.metadata.create_all(conn)

def _get_config_value(session: Session, key: str) -> Optional[str]:
    row = session.scalar(select(ConfigKV).where(ConfigKV.key == key))
    return row.value if row else None

def _set_config_value(session: Session, key: str, value: str):
    row = session.scalar(select(ConfigKV).where(ConfigKV.key == key))
    if row:
        row.value = value
    else:
        row = ConfigKV(key=key, value=value)
        session.add(row)

# === 高層 API：Site / Schedule ===
def get_site() -> Site:
    with Session(engine) as s:
        v = _get_config_value(s, "site")
        return json_str_to_model(v, Site)

def set_site(payload: dict) -> Site:
    site = Site(**payload)
    with Session(engine) as s:
        _set_config_value(s, "site", model_to_json_str(site))
        s.commit()
    return site

def get_schedule() -> Schedule:
    with Session(engine) as s:
        v = _get_config_value(s, "schedule")
        return json_str_to_model(v, Schedule)

def set_schedule(payload: dict) -> Schedule:
    sch = Schedule(**payload)
    with Session(engine) as s:
        _set_config_value(s, "schedule", model_to_json_str(sch))
        s.commit()
    return sch

# ============== 使用者工具（仍用 JSON，保留你現況流程） ==============
def get_users():
    return get_("users") or []

def upsert_user(user: dict):
    users = get_("users") or []
    # 依 id 存在就更新，否則新增
    idx = next((i for i, u in enumerate(users) if u.get("id") == user.get("id")), -1)
    if idx >= 0:
        users[idx] = user
    else:
        users.append(user)
    set_("users", users)

def find_user_by_account(account: str) -> Optional[dict]:
    users = get_("users") or []
    account = (account or "").strip().lower()
    return next((u for u in users if (u.get("account","").strip().lower() == account)), None)

def save_users(users: list):
    set_("users", users)
