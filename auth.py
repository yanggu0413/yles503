from flask import Blueprint, request, jsonify, session, make_response
from datetime import datetime, timedelta
import os
from models import db, User, Config

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@bp.post("/login")
def login():
    data = request.json or {}
    acc, pw = (data.get("account") or "").strip(), (data.get("password") or "")

    # basic validation
    if not acc or not pw:
        return jsonify({"error": "請提供帳號與密碼"}), 400

    # lockout / rate limiting settings (env override)
    try:
        MAX_TRIES = int(os.getenv('LOGIN_MAX_TRIES', '6'))
    except:
        MAX_TRIES = 6
    try:
        LOCK_SECONDS = int(os.getenv('LOGIN_LOCK_SECONDS', '900'))
    except:
        LOCK_SECONDS = 900

    # check existing lock
    lock_key = f"login_lock:{acc}"
    fail_key = f"login_fail:{acc}"
    locked_until_s = Config.get(lock_key)
    now_ts = int(datetime.utcnow().timestamp())
    if locked_until_s:
        try:
            locked_until = int(locked_until_s)
            if now_ts < locked_until:
                return jsonify({"error": "帳號暫時鎖定，請稍後再試"}), 429
        except:
            pass

    user = User.query.filter_by(account=acc).first()
    if not user or not user.check_password(pw):
        # increment failure count
        try:
            cur = int(Config.get(fail_key) or '0')
        except:
            cur = 0
        cur += 1
        Config.set(fail_key, str(cur))
        if cur >= MAX_TRIES:
            lock_ts = now_ts + LOCK_SECONDS
            Config.set(lock_key, str(lock_ts))
            Config.set(fail_key, '0')
        db.session.commit()
        return jsonify({"error": "帳號或密碼錯誤"}), 401

    if not user.enabled:
        return jsonify({"error": "帳號已停用"}), 403

    # successful login: clear fail counters
    Config.set(fail_key, '0')
    Config.set(lock_key, '')
    db.session.commit()

    session["uid"] = user.id
    payload = {"id": user.id, "account": user.account, "name": user.name, "role": user.role}
    # Echo Origin and allow credentials so browser will accept the session cookie
    origin = request.headers.get("Origin")
    resp = make_response(jsonify(payload))
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Vary"] = "Origin"
    return resp

@bp.get("/me")
def me():
    uid = session.get("uid")
    if not uid:
        resp = make_response(jsonify(None))
        origin = request.headers.get("Origin")
        if origin:
            resp.headers["Access-Control-Allow-Origin"] = origin
        else:
            resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Vary"] = "Origin"
        return resp
    u = User.query.get(uid)
    payload = {"id": u.id, "account": u.account, "name": u.name, "role": u.role}
    resp = make_response(jsonify(payload))
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Vary"] = "Origin"
    return resp

@bp.post("/logout")
def logout():
    session.clear()
    resp = make_response(jsonify({"ok": True}))
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Vary"] = "Origin"
    return resp
