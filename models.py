# models.py
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ---- 共用 mixin ----
class TimestampMixin(object):
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# ---- 站台設定（Key-Value）----
class Config(db.Model):
    __tablename__ = 'config'
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=True)

    @staticmethod
    def get(key, default=None):
        row = Config.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = Config.query.filter_by(key=key).first()
        if not row:
            row = Config(key=key, value=value)
            db.session.add(row)
        else:
            row.value = value
        return row

# ---- 使用者 ----
class User(db.Model, TimestampMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.String(64), unique=True, index=True, nullable=False)
    name = db.Column(db.String(128), nullable=True)
    role = db.Column(db.String(16), default='student', nullable=False)  # student / teacher / admin
    password_hash = db.Column(db.String(200), nullable=False)
    enabled = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def to_dict(self):
        return {
            'id': self.id,
            'account': self.account,
            'name': self.name,
            'role': self.role,
            'enabled': self.enabled,
            'createdAt': self.created_at.isoformat() + 'Z',
            'updatedAt': self.updated_at.isoformat() + 'Z',
        }

    def to_dict_admin(self):
        d = self.to_dict()
        # 不回傳 hash
        return d

# ---- 公告 ----
class Announcement(db.Model, TimestampMixin):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'createdAt': self.created_at.isoformat() + 'Z',
            'updatedAt': self.updated_at.isoformat() + 'Z',
        }

# ---- 作業 ----
class Assignment(db.Model, TimestampMixin):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(64), nullable=True)
    due = db.Column(db.String(20), nullable=True)     # 直接存 yyyy-mm-dd
    status = db.Column(db.String(16), default='open') # open/closed
    detail = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'subject': self.subject,
            'due': self.due,
            'status': self.status,
            'detail': self.detail,
            'createdAt': self.created_at.isoformat() + 'Z',
            'updatedAt': self.updated_at.isoformat() + 'Z',
        }

# ---- 資源 ----
class Resource(db.Model, TimestampMixin):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(64), nullable=True)
    desc = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'category': self.category,
            'desc': self.desc,
            'createdAt': self.created_at.isoformat() + 'Z',
            'updatedAt': self.updated_at.isoformat() + 'Z',
        }

# ---- 相簿 ----
class GalleryItem(db.Model, TimestampMixin):
    __tablename__ = 'gallery'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    url = db.Column(db.String(500), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'createdAt': self.created_at.isoformat() + 'Z',
            'updatedAt': self.updated_at.isoformat() + 'Z',
        }

# ---- 班規 ----
class Rule(db.Model, TimestampMixin):
    __tablename__ = 'rules'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'createdAt': self.created_at.isoformat() + 'Z',
            'updatedAt': self.updated_at.isoformat() + 'Z',
        }

# ---- 初始化 ----
def init_db():
    """初始化資料庫並建立預設管理員"""
    try:
        # 解析資料庫路徑
        db_uri = os.getenv("DB_URL", "sqlite:///app.db")
        if db_uri.startswith("sqlite:///"):
            db_file = db_uri.replace("sqlite:///", "")
            folder = os.path.dirname(db_file)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)

        # 建立資料表
        db.create_all()

        # 建立預設管理員
        from models import User  # 延遲匯入以避免循環依賴
        if not User.query.filter_by(account='admin').first():
            admin = User(account='admin', name='系統管理員', role='admin')
            admin.set_password('admin123')  # ⚠️ 部署後請立即修改！
            db.session.add(admin)
            db.session.commit()

        print("✅ Database initialized successfully.")

    except Exception as e:
        print("⚠️ init_db 發生錯誤:", e)
