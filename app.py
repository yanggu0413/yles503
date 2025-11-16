import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask import send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash

# ---------------------
# Flask App 基本設定
# ---------------------
# 將前端靜態檔案（位於專案的 `前端` 資料夾）交由 Flask 提供，讓前後端同源以利 Cookie/Session 運作
static_root = os.path.join(os.getcwd(), '前端')
app = Flask(__name__, static_folder=static_root, static_url_path='')

# --- Session 設定 ---
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# 開發模式下不要把 session cookie 設為 secure（否則在 http 本機會被瀏覽器忽略）
if os.getenv('FLASK_DEBUG', '1') == '1' or os.getenv('DEBUG', 'true').lower() in ('1','true'):
    app.config['SESSION_COOKIE_SECURE'] = False

# --- CORS 設定 ---
# 允許 /api/* 的跨域請求（保留開發時常用的 localhost/127 等）
# 注意：若前端由同一個 Flask 提供（如在 dev 會這樣），跨域就不會發生；但保留常見本機 origin
CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8787", "http://127.0.0.1:8787"]}})

# ---------------------
# 資料庫設定
# ---------------------
db_url = os.getenv("DB_URL", "sqlite:///app.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Use models.py SQLAlchemy instance to avoid duplicated model definitions
from models import db as models_db, User as ModelsUser

# initialize models' db with app
models_db.init_app(app)

# alias for convenience
db = models_db



# ---------------------
# 初始化資料庫
# ---------------------
def init_db():
    try:
        db_path = db_url.replace("sqlite:///", "")
        folder = os.path.dirname(db_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        with app.app_context():
            db.create_all()

            # 建立內建管理員（models.User）
            if not ModelsUser.query.filter_by(account="admin").first():
                admin = ModelsUser(account="admin", name="系統管理員", role="admin")
                admin.set_password("admin123")
                db.session.add(admin)
                db.session.commit()
                print("✅ 建立預設管理員 admin / admin123")

        print(f"✅ Database ready at: {db_url}")

    except Exception as e:
        print("⚠️ init_db 發生錯誤:", e)


# ---------------------
# Blueprint 模組註冊
# ---------------------
from auth import bp as auth_bp
app.register_blueprint(auth_bp)

# register admin blueprint if present
try:
    from admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
except Exception:
    # if admin blueprint missing or has errors, continue; developer should check logs
    pass

# serve media files under /media/<path:filename>
@app.route('/media/<path:filename>')
def media_file(filename):
    media_root = os.path.join(os.getcwd(), 'media')
    return send_from_directory(media_root, filename)

# 你可以繼續在這裡註冊其他模組，例如：
# from admin import bp as admin_bp
# from siteinfo import bp as site_bp
# from announcement import bp as ann_bp
# app.register_blueprint(admin_bp)
# app.register_blueprint(site_bp)
# app.register_blueprint(ann_bp)


# ---------------------
# 健康檢查 API
# ---------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ---------------------
# 啟動伺服器
# ---------------------
if __name__ == "__main__":
    init_db()
    # 啟動 Flask 伺服器，同時提供前端靜態檔案，方便本機開發測試（前端請透過 http://localhost:8787 開啟）
    app.run(host="0.0.0.0", port=8787, debug=True)
