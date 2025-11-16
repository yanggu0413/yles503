# admin.py
import os
import time
from functools import wraps

from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename

from models import db, User, Announcement, Assignment, Resource, GalleryItem, Rule, Config

admin_bp = Blueprint('admin', __name__)

# 媒體資料夾
MEDIA_DIR = os.path.join(os.getcwd(), 'media')
os.makedirs(MEDIA_DIR, exist_ok=True)

ALLOWED_SCHEDULE_MIMES = {
    'image/png': '.png',
    'image/jpeg': '.jpg',
    'image/svg+xml': '.svg',
}

# ====== 權限輔助 ======
def current_user():
    # auth.py stores uid in session['uid']
    uid = session.get('uid')
    if not uid:
        return None
    return User.query.get(uid)

def require_roles(roles=('teacher', 'admin')):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = current_user()
            if not u:
                return jsonify({'ok': False, 'message': '請先登入'}), 401
            if roles and u.role not in roles:
                return jsonify({'ok': False, 'message': '權限不足'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return deco

# ====== 站台設定 ======
@admin_bp.get('/site')
@require_roles()
def admin_get_site():
    data = {
        'schoolName': Config.get('schoolName'),
        'className' : Config.get('className'),
        'subtitle'  : Config.get('subtitle'),
        'teacherName': Config.get('teacherName'),
        'contactEmail': Config.get('contactEmail'),
    }
    return jsonify(data)

@admin_bp.put('/site')
@require_roles()
def admin_save_site():
    body = request.get_json(silent=True) or {}
    for k in ['schoolName','className','subtitle','teacherName','contactEmail']:
        Config.set(k, (body.get(k) or '').strip() or None)
    db.session.commit()
    return jsonify({'ok': True})

# ====== 公告 ======
@admin_bp.get('/announcements')
@require_roles()
def admin_list_ann():
    items = Announcement.query.order_by(Announcement.updated_at.desc(), Announcement.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])

@admin_bp.post('/announcements')
@require_roles()
def admin_create_ann():
    body = request.get_json(silent=True) or {}
    a = Announcement(
        title=(body.get('title') or '').strip(),
        content=(body.get('content') or '').strip(),
    )
    db.session.add(a); db.session.commit()
    return jsonify(a.to_dict())

@admin_bp.put('/announcements/<int:aid>')
@require_roles()
def admin_update_ann(aid):
    a = Announcement.query.get_or_404(aid)
    body = request.get_json(silent=True) or {}
    a.title = (body.get('title') or '').strip()
    a.content = (body.get('content') or '').strip()
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.delete('/announcements/<int:aid>')
@require_roles()
def admin_delete_ann(aid):
    a = Announcement.query.get_or_404(aid)
    db.session.delete(a); db.session.commit()
    return jsonify({'ok': True})

# ====== 作業 ======
@admin_bp.get('/assignments')
@require_roles()
def admin_list_asg():
    items = Assignment.query.order_by(Assignment.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])

@admin_bp.post('/assignments')
@require_roles()
def admin_create_asg():
    body = request.get_json(silent=True) or {}
    a = Assignment(
        title=(body.get('title') or '').strip(),
        subject=(body.get('subject') or '').strip() or None,
        due=(body.get('due') or None),
        status=(body.get('status') or 'open'),
        detail=(body.get('detail') or '').strip() or None,
    )
    db.session.add(a); db.session.commit()
    return jsonify(a.to_dict())

@admin_bp.put('/assignments/<int:aid>')
@require_roles()
def admin_update_asg(aid):
    a = Assignment.query.get_or_404(aid)
    body = request.get_json(silent=True) or {}
    a.title = (body.get('title') or '').strip()
    a.subject = (body.get('subject') or '').strip() or None
    a.due = (body.get('due') or None)
    a.status = (body.get('status') or 'open')
    a.detail = (body.get('detail') or '').strip() or None
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.delete('/assignments/<int:aid>')
@require_roles()
def admin_delete_asg(aid):
    a = Assignment.query.get_or_404(aid)
    db.session.delete(a); db.session.commit()
    return jsonify({'ok': True})

# ====== 資源 ======
@admin_bp.get('/resources')
@require_roles()
def admin_list_res():
    items = Resource.query.order_by(Resource.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])

@admin_bp.post('/resources')
@require_roles()
def admin_create_res():
    body = request.get_json(silent=True) or {}
    r = Resource(
        title=(body.get('title') or '').strip(),
        url=(body.get('url') or '').strip(),
        category=(body.get('category') or '').strip() or None,
        desc=(body.get('desc') or '').strip() or None,
    )
    db.session.add(r); db.session.commit()
    return jsonify(r.to_dict())

@admin_bp.put('/resources/<int:rid>')
@require_roles()
def admin_update_res(rid):
    r = Resource.query.get_or_404(rid)
    body = request.get_json(silent=True) or {}
    r.title = (body.get('title') or '').strip()
    r.url = (body.get('url') or '').strip()
    r.category = (body.get('category') or '').strip() or None
    r.desc = (body.get('desc') or '').strip() or None
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.delete('/resources/<int:rid>')
@require_roles()
def admin_delete_res(rid):
    r = Resource.query.get_or_404(rid)
    db.session.delete(r); db.session.commit()
    return jsonify({'ok': True})

# ====== 相簿 ======
@admin_bp.get('/gallery')
@require_roles()
def admin_list_gallery():
    items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])

@admin_bp.post('/gallery')
@require_roles()
def admin_create_gallery():
    body = request.get_json(silent=True) or {}
    g = GalleryItem(
        title=(body.get('title') or '').strip() or None,
        url=(body.get('url') or '').strip(),
    )
    db.session.add(g); db.session.commit()
    return jsonify(g.to_dict())

@admin_bp.put('/gallery/<int:gid>')
@require_roles()
def admin_update_gallery(gid):
    g = GalleryItem.query.get_or_404(gid)
    body = request.get_json(silent=True) or {}
    g.title = (body.get('title') or '').strip() or None
    g.url = (body.get('url') or '').strip()
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.delete('/gallery/<int:gid>')
@require_roles()
def admin_delete_gallery(gid):
    g = GalleryItem.query.get_or_404(gid)
    db.session.delete(g); db.session.commit()
    return jsonify({'ok': True})

# ====== 班規 ======
@admin_bp.get('/rules')
@require_roles()
def admin_list_rules():
    items = Rule.query.order_by(Rule.created_at.desc()).all()
    return jsonify([i.to_dict() for i in items])

@admin_bp.post('/rules')
@require_roles()
def admin_create_rule():
    body = request.get_json(silent=True) or {}
    r = Rule(
        title=(body.get('title') or '').strip(),
        content=(body.get('content') or '').strip(),
    )
    db.session.add(r); db.session.commit()
    return jsonify(r.to_dict())

@admin_bp.put('/rules/<int:rid>')
@require_roles()
def admin_update_rule(rid):
    r = Rule.query.get_or_404(rid)
    body = request.get_json(silent=True) or {}
    r.title = (body.get('title') or '').strip()
    r.content = (body.get('content') or '').strip()
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.delete('/rules/<int:rid>')
@require_roles()
def admin_delete_rule(rid):
    r = Rule.query.get_or_404(rid)
    db.session.delete(r); db.session.commit()
    return jsonify({'ok': True})

# ====== 使用者管理 ======
@admin_bp.get('/users')
@require_roles(('admin',))  # 只有 admin 可以管理使用者
def admin_list_users():
    items = User.query.order_by(User.created_at.desc()).all()
    return jsonify([i.to_dict_admin() for i in items])

@admin_bp.post('/users')
@require_roles(('admin',))
def admin_create_user():
    body = request.get_json(silent=True) or {}
    account = (body.get('account') or '').strip()
    if not account:
        return jsonify({'ok': False, 'message': '帳號必填'}), 400
    if User.query.filter_by(account=account).first():
        return jsonify({'ok': False, 'message': '帳號已存在'}), 409
    u = User(
        account=account,
        name=(body.get('name') or '').strip() or None,
        role=(body.get('role') or 'student'),
    )
    pwd = body.get('password')
    if not pwd or len(pwd) < 6:
        return jsonify({'ok': False, 'message': '密碼至少 6 碼'}), 400
    u.set_password(pwd)
    db.session.add(u); db.session.commit()
    return jsonify(u.to_dict_admin())

@admin_bp.put('/users/<int:uid>')
@require_roles(('admin',))
def admin_update_user(uid):
    u = User.query.get_or_404(uid)
    body = request.get_json(silent=True) or {}
    if 'name' in body:
        u.name = (body.get('name') or '').strip() or None
    if 'role' in body:
        u.role = (body.get('role') or 'student')
    if 'enabled' in body:
        enabled = body.get('enabled')
        u.enabled = bool(enabled)
    if 'password' in body and (body.get('password') or '').strip():
        pwd = body.get('password').strip()
        if len(pwd) < 6:
            return jsonify({'ok': False, 'message': '密碼至少 6 碼'}), 400
        u.set_password(pwd)
    db.session.commit()
    return jsonify({'ok': True})

@admin_bp.delete('/users/<int:uid>')
@require_roles(('admin',))
def admin_delete_user(uid):
    u = User.query.get_or_404(uid)
    db.session.delete(u); db.session.commit()
    return jsonify({'ok': True})

@admin_bp.post('/users/<int:uid>/reset-password')
@require_roles(('admin',))
def admin_reset_password(uid):
    u = User.query.get_or_404(uid)
    body = request.get_json(silent=True) or {}
    pwd = (body.get('newPassword') or body.get('password') or '').strip()
    if len(pwd) < 6:
        return jsonify({'ok': False, 'message': '密碼至少 6 碼'}), 400
    u.set_password(pwd); db.session.commit()
    return jsonify({'ok': True})

# ====== 課表圖片 ======
@admin_bp.post('/schedule/image')
@require_roles()
def upload_schedule_image():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'message': '缺少檔案'}), 400
    f = request.files['file']
    if not f or f.filename == '':
        return jsonify({'ok': False, 'message': '未選擇檔案'}), 400
    mime = f.mimetype or ''
    if mime not in ALLOWED_SCHEDULE_MIMES:
        return jsonify({'ok': False, 'message': '檔案格式不支援，請上傳 png/jpg/svg'}), 400

    subdir = os.path.join(MEDIA_DIR, 'schedule')
    os.makedirs(subdir, exist_ok=True)
    ext = ALLOWED_SCHEDULE_MIMES[mime]
    filename = f"schedule-{int(time.time())}{ext}"
    path = os.path.join(subdir, secure_filename(filename))
    f.save(path)

    public_url = f"/media/schedule/{filename}"
    Config.set('scheduleImage', public_url)
    db.session.commit()
    return jsonify({'ok': True, 'imageUrl': public_url})

@admin_bp.delete('/schedule/image')
@require_roles()
def delete_schedule_image():
    img = Config.get('scheduleImage')
    if img:
        try:
            full = os.path.join(MEDIA_DIR, img.lstrip('/'))
            if os.path.isfile(full):
                os.remove(full)
        except Exception:
            pass
        Config.set('scheduleImage', None)
        db.session.commit()
    return jsonify({'ok': True})
