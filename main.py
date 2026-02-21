# main.py
import os
import json
import time
import shutil
from typing import List, Any
from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request, UploadFile, File, APIRouter, Path
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

# Import local modules
import models
import schemas
from database import get_db
from models import create_all_tables
from auth_fastapi import (
    authenticate_user, create_access_token, get_current_user, require_roles,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)

# --- App Initialization ---
app = FastAPI(title="雲林國小 五年三班 班網 API 端點", version="1.0.0")

# --- Database Initialization ---
@app.on_event("startup")
def on_startup():
    print("Application startup...")
    create_all_tables()

# --- CORS Middleware ---
allowed_origins = [
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:8787", "http://127.0.0.1:8787",
    "http://localhost:3000",
    "http://localhost:5173", "http://127.0.0.1:5173",
    "https://yles503.tw", "https://www.yles503.tw", "https://api.yles503.tw",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])
public_router = APIRouter(prefix="/api", tags=["Public"])
admin_router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(require_roles(('teacher', 'admin')))]
)
user_admin_router = APIRouter(
    prefix="/api/admin/users",
    tags=["Admin - Users"],
    dependencies=[Depends(require_roles(('admin',)))]
)


# --- Authentication Endpoints (auth_router) ---
@auth_router.post("/login", response_model=schemas.Token)
async def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect account or password", {"WWW-Authenticate": "Bearer"})
        if not user.enabled:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is disabled")
        
        access_token = create_access_token(data={"sub": user.account})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Server error during login")

@auth_router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@auth_router.post("/logout")
async def logout():
    return {"ok": True}


# --- Public API Endpoints (public_router) ---
@public_router.get("/site", response_model=schemas.SiteInfo)
def public_site(db: Session = Depends(get_db)):
    keys = ["schoolName", "className", "subtitle", "teacherName", "contactEmail", "scheduleImage"]
    configs = db.query(models.Config).filter(models.Config.key.in_(keys)).all()
    return {c.key: c.value for c in configs}

@public_router.get("/announcements", response_model=List[schemas.Announcement])
def public_announcements(db: Session = Depends(get_db)):
    return db.query(models.Announcement).order_by(models.Announcement.updated_at.desc()).all()

@public_router.get("/schedule")
def public_schedule(db: Session = Depends(get_db)):
    config = db.query(models.Config).filter(models.Config.key == 'schedule').first()
    config_image = db.query(models.Config).filter(models.Config.key == 'scheduleImage').first()
    result = {}
    if config and config.value:
        try: result = json.loads(config.value)
        except: result = {"value": config.value}
    if config_image and config_image.value:
        result["scheduleImage"] = config_image.value
    return result if result else None

@public_router.get("/assignments", response_model=List[schemas.Assignment])
def public_assignments(db: Session = Depends(get_db)):
    return db.query(models.Assignment).order_by(models.Assignment.created_at.desc()).all()

@public_router.get("/resources", response_model=List[schemas.Resource])
def public_resources(db: Session = Depends(get_db)):
    return db.query(models.Resource).order_by(models.Resource.created_at.desc()).all()

@public_router.get("/gallery", response_model=List[schemas.GalleryItem])
def public_gallery(db: Session = Depends(get_db)):
    return db.query(models.GalleryItem).order_by(models.GalleryItem.created_at.desc()).all()

@public_router.get("/rules", response_model=List[schemas.Rule])
def public_rules(db: Session = Depends(get_db)):
    return db.query(models.Rule).order_by(models.Rule.created_at.desc()).all()


# --- Admin API Endpoints (admin_router) ---

# Site Management
@admin_router.get("/site", response_model=schemas.SiteInfo)
def admin_get_site(db: Session = Depends(get_db)):
    return public_site(db)

@admin_router.put("/site", response_model=schemas.SiteInfo)
def admin_update_site(site_info: schemas.SiteInfo, db: Session = Depends(get_db)):
    for key, value in site_info.model_dump().items():
        config_item = db.query(models.Config).filter(models.Config.key == key).first()
        if not config_item:
            config_item = models.Config(key=key)
            db.add(config_item)
        config_item.value = value
    db.commit()
    return public_site(db)

# Schedule
@admin_router.get("/schedule")
def admin_get_schedule(db: Session = Depends(get_db)):
    config = db.query(models.Config).filter(models.Config.key == 'scheduleImage').first()
    return {"scheduleImage": config.value if config else None}

@admin_router.put("/schedule")
def admin_update_schedule(schedule_data: dict, db: Session = Depends(get_db)):
    if 'scheduleImage' in schedule_data:
        config_item = db.query(models.Config).filter(models.Config.key == 'scheduleImage').first()
        if not config_item:
            config_item = models.Config(key='scheduleImage')
            db.add(config_item)
        config_item.value = schedule_data['scheduleImage']
        db.commit()
    return {"scheduleImage": schedule_data.get('scheduleImage')}

# Schedule Image Upload
@admin_router.post("/schedule/image", response_model=schemas.ScheduleImage)
async def upload_schedule_image(db: Session = Depends(get_db), file: UploadFile = File(...)):
    ALLOWED_MIMES = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/svg+xml': '.svg'}
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File format not supported. Please upload png/jpg/svg")

    MEDIA_DIR = os.path.join(os.getcwd(), "media")
    subdir = os.path.join(MEDIA_DIR, "schedule")
    os.makedirs(subdir, exist_ok=True)
    
    ext = ALLOWED_MIMES[file.content_type]
    filename = f"schedule-{int(time.time())}{ext}"
    save_path = os.path.join(subdir, secure_filename(filename))

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    public_url = f"/media/schedule/{filename}"
    
    config_item = db.query(models.Config).filter(models.Config.key == 'scheduleImage').first()
    if not config_item:
        config_item = models.Config(key='scheduleImage')
        db.add(config_item)
    config_item.value = public_url
    db.commit()

    return {"imageUrl": public_url}

@admin_router.delete("/schedule/image", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_image(db: Session = Depends(get_db)):
    config_item = db.query(models.Config).filter(models.Config.key == 'scheduleImage').first()
    if config_item and config_item.value:
        try:
            media_path = os.path.join(os.getcwd(), "media")
            full_path = os.path.join(media_path, config_item.value.lstrip('/media/'))
            if os.path.isfile(full_path):
                os.remove(full_path)
        except Exception as e:
            print(f"Error deleting schedule image file: {e}") # Log error but proceed
        
        config_item.value = None
        db.commit()

# Generic CRUD Functions
def get_item_list(db: Session, model: Any):
    return db.query(model).order_by(model.created_at.desc()).all()

def create_item(db: Session, model: Any, schema: schemas.BaseModel):
    db_item = model(**schema.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

def update_item(db: Session, item: Any, schema: schemas.BaseModel):
    for key, value in schema.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

def delete_item(db: Session, item: Any):
    db.delete(item)
    db.commit()

# Announcements
@admin_router.get("/announcements", response_model=List[schemas.Announcement])
def admin_list_announcements(db: Session = Depends(get_db)): return get_item_list(db, models.Announcement)
@admin_router.post("/announcements", response_model=schemas.Announcement, status_code=status.HTTP_201_CREATED)
def admin_create_announcement(ann: schemas.AnnouncementCreate, db: Session = Depends(get_db)): return create_item(db, models.Announcement, ann)
@admin_router.put("/announcements/{item_id}", response_model=schemas.Announcement)
def admin_update_announcement(item_id: int, ann: schemas.AnnouncementUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Announcement, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    return update_item(db, item, ann)
@admin_router.delete("/announcements/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_announcement(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Announcement, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    delete_item(db, item)

# Assignments
@admin_router.get("/assignments", response_model=List[schemas.Assignment])
def admin_list_assignments(db: Session = Depends(get_db)): return get_item_list(db, models.Assignment)
@admin_router.post("/assignments", response_model=schemas.Assignment, status_code=status.HTTP_201_CREATED)
def admin_create_assignment(asn: schemas.AssignmentCreate, db: Session = Depends(get_db)): return create_item(db, models.Assignment, asn)
@admin_router.put("/assignments/{item_id}", response_model=schemas.Assignment)
def admin_update_assignment(item_id: int, asn: schemas.AssignmentUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Assignment, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    return update_item(db, item, asn)
@admin_router.delete("/assignments/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_assignment(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Assignment, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    delete_item(db, item)

# Resources
@admin_router.get("/resources", response_model=List[schemas.Resource])
def admin_list_resources(db: Session = Depends(get_db)): return get_item_list(db, models.Resource)
@admin_router.post("/resources", response_model=schemas.Resource, status_code=status.HTTP_201_CREATED)
def admin_create_resource(res: schemas.ResourceCreate, db: Session = Depends(get_db)): return create_item(db, models.Resource, res)
@admin_router.put("/resources/{item_id}", response_model=schemas.Resource)
def admin_update_resource(item_id: int, res: schemas.ResourceUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Resource, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    return update_item(db, item, res)
@admin_router.delete("/resources/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_resource(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Resource, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    delete_item(db, item)

# Gallery
@admin_router.get("/gallery", response_model=List[schemas.GalleryItem])
def admin_list_gallery(db: Session = Depends(get_db)): return get_item_list(db, models.GalleryItem)
@admin_router.post("/gallery", response_model=schemas.GalleryItem, status_code=status.HTTP_201_CREATED)
def admin_create_gallery_item(gal: schemas.GalleryItemCreate, db: Session = Depends(get_db)): return create_item(db, models.GalleryItem, gal)
@admin_router.put("/gallery/{item_id}", response_model=schemas.GalleryItem)
def admin_update_gallery_item(item_id: int, gal: schemas.GalleryItemUpdate, db: Session = Depends(get_db)):
    item = db.get(models.GalleryItem, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    return update_item(db, item, gal)
@admin_router.delete("/gallery/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_gallery_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.GalleryItem, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    try:
        if item.url and item.url.startswith('/media/'):
            media_path = os.path.join(os.getcwd(), item.url.lstrip('/media/'))
            if os.path.isfile(media_path):
                os.remove(media_path)
    except Exception as e:
        print(f"Error deleting gallery file: {e}")
    delete_item(db, item)

@admin_router.post("/gallery/upload", response_model=schemas.GalleryItem, status_code=status.HTTP_201_CREATED)
async def upload_gallery_image(db: Session = Depends(get_db), file: UploadFile = File(...), title: str = None):
    ALLOWED_MIMES = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/gif': '.gif', 'image/webp': '.webp', 'image/svg+xml': '.svg'}
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File format not supported")
    
    MEDIA_DIR = os.path.join(os.getcwd(), "media")
    subdir = os.path.join(MEDIA_DIR, "gallery")
    os.makedirs(subdir, exist_ok=True)
    
    ext = ALLOWED_MIMES[file.content_type]
    filename = f"gallery-{int(time.time())}{ext}"
    save_path = os.path.join(subdir, secure_filename(filename))

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    public_url = f"/media/gallery/{filename}"
    
    gallery_item = models.GalleryItem(
        title=title or file.filename,
        url=public_url
    )
    db.add(gallery_item)
    db.commit()
    db.refresh(gallery_item)
    return gallery_item

# Rules
@admin_router.get("/rules", response_model=List[schemas.Rule])
def admin_list_rules(db: Session = Depends(get_db)): return get_item_list(db, models.Rule)
@admin_router.post("/rules", response_model=schemas.Rule, status_code=status.HTTP_201_CREATED)
def admin_create_rule(rule: schemas.RuleCreate, db: Session = Depends(get_db)): return create_item(db, models.Rule, rule)
@admin_router.put("/rules/{item_id}", response_model=schemas.Rule)
def admin_update_rule(item_id: int, rule: schemas.RuleUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Rule, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    return update_item(db, item, rule)
@admin_router.delete("/rules/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_rule(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Rule, item_id)
    if not item: raise HTTPException(status.HTTP_404_NOT_FOUND)
    delete_item(db, item)


# --- User Admin API Endpoints (user_admin_router) ---
@user_admin_router.get("", response_model=List[schemas.User])
def admin_list_users(db: Session = Depends(get_db)):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()

@user_admin_router.post("", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def admin_create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.account == user.account).first()
    if db_user:
        raise HTTPException(status.HTTP_409_CONFLICT, "Account already exists")
    
    hashed_password = get_password_hash(user.password)
    db_user = models.User(**user.model_dump(exclude={'password'}), password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@user_admin_router.put("/{user_id}", response_model=schemas.User)
def admin_update_user(user_id: int, user_update: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.get(models.User, user_id)
    if not db_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    update_data = user_update.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        db_user.password_hash = get_password_hash(update_data["password"])
        del update_data["password"]
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
        
    db.commit()
    db.refresh(db_user)
    return db_user

@user_admin_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.get(models.User, user_id)
    if not db_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    delete_item(db, db_user)

@user_admin_router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def admin_reset_user_password(user_id: int, new_password_data: schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = db.get(models.User, user_id)
    if not db_user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if not new_password_data.password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "New password not provided")

    db_user.password_hash = get_password_hash(new_password_data.password)
    db.commit()


# Include all routers
app.include_router(auth_router)
app.include_router(public_router)
app.include_router(admin_router)
app.include_router(user_admin_router)


# --- Static Files Mounting ---
media_path = os.path.join(os.getcwd(), "media")
if not os.path.exists(media_path):
    os.makedirs(media_path)
app.mount("/media", StaticFiles(directory=media_path), name="media")

# --- 羊咕註解：因為前端資料夾不存在，暫時移除掛載 ---
# static_root = os.path.join(os.getcwd(), '..', '前端')
# app.mount("/", StaticFiles(directory=static_root, html=True), name="static")


# --- Health Check and Fallback ---
@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "message": "API is running"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Server error, please try again later"}
    )

@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    # 如果是 API 或 Media 找不到，直接回傳 JSON 404
    if request.url.path.startswith(("/api/", "/media/")):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not Found"})
    
    # 羊咕註解：因為目前沒有前端，所有非 API 的請求都回傳純文字或 JSON
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, 
        content={"detail": "API 運行中，但找不到前端靜態網頁資源。"}
    )
    

if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8787, reload=True)
