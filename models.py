from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from database import Base
import os

# ---- 共用 mixin ----
class TimestampMixin(object):
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# ---- 站台設定（Key-Value）----
class Config(Base):
    __tablename__ = 'config'
    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=True)

# ---- 使用者 ----
class User(Base, TimestampMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    account = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=True)
    role = Column(String(16), default='student', nullable=False)
    password_hash = Column(String(200), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    failed = Column(Integer, default=0, nullable=False)
    locked_until = Column(Integer, default=0, nullable=False)
    last_login_at = Column(Integer, nullable=True)

# ---- 公告 ----
class Announcement(Base, TimestampMixin):
    __tablename__ = 'announcements'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)

# ---- 作業 ----
class Assignment(Base, TimestampMixin):
    __tablename__ = 'assignments'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    subject = Column(String(64), nullable=True)
    due = Column(String(20), nullable=True)     # 直接存 yyyy-mm-dd
    status = Column(String(16), default='open') # open/closed
    detail = Column(Text, nullable=True)

# ---- 資源 ----
class Resource(Base, TimestampMixin):
    __tablename__ = 'resources'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    category = Column(String(64), nullable=True)
    desc = Column(Text, nullable=True)

# ---- 相簿 ----
class GalleryItem(Base, TimestampMixin):
    __tablename__ = 'gallery'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=True)
    url = Column(String(500), nullable=False)

# ---- 班規 ----
class Rule(Base, TimestampMixin):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)

# ---- 操作稽核 (Audit) ----
class Audit(Base):
    __tablename__ = 'audits'
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, nullable=True, index=True)
    actor_name = Column(String(128), nullable=True)
    action = Column(String(128), nullable=False)
    object_type = Column(String(64), nullable=True)
    object_id = Column(String(64), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def create_all_tables():
    """建立所有資料表"""
    try:
        # We can use the engine from database.py
        from database import engine
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("[Success] Tables created successfully.")
        
        # Optionally, create a default admin user if one doesn't exist
        from database import SessionLocal
        from auth_fastapi import get_password_hash

        db = SessionLocal()
        if not db.query(User).filter_by(account='admin').first():
            admin = User(
                account='admin', 
                name='系統管理員', 
                role='admin',
                password_hash=get_password_hash('admin123')
            )
            db.add(admin)
            db.commit()
            print("[Success] Created default admin user (admin / admin123)")
        db.close()

    except Exception as e:
        print(f"[Error] An error occurred during table creation: {e}")

