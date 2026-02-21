# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# =================
# Base Schemas
# =================

# --- Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    account: Optional[str] = None

# --- User ---
class UserBase(BaseModel):
    account: str = Field(..., min_length=3, max_length=64)
    name: Optional[str] = Field(None, max_length=128)
    role: str = Field('student', pattern="^(student|teacher|admin)$")
    enabled: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    role: Optional[str] = Field(None, pattern="^(student|teacher|admin)$")
    enabled: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)

class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class User(UserInDB):
    pass

class UserSelf(User):
    # For the /api/auth/me endpoint
    pass


# --- Config (Site Info) ---
class SiteInfo(BaseModel):
    schoolName: Optional[str] = None
    className: Optional[str] = None
    subtitle: Optional[str] = None
    teacherName: Optional[str] = None
    contactEmail: Optional[str] = None
    scheduleImage: Optional[str] = None


# --- Announcement ---
class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: Optional[str] = None

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementUpdate(AnnouncementBase):
    pass

class Announcement(AnnouncementBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Assignment ---
class AssignmentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    subject: Optional[str] = Field(None, max_length=64)
    due: Optional[str] = Field(None)
    status: str = Field('open', pattern="^(open|closed)$")
    detail: Optional[str] = None

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentUpdate(AssignmentBase):
    pass

class Assignment(AssignmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Resource ---
class ResourceBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = Field(None, max_length=64)
    desc: Optional[str] = None

class ResourceCreate(ResourceBase):
    pass

class ResourceUpdate(ResourceBase):
    pass

class Resource(ResourceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Gallery Item ---
class GalleryItemBase(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    url: str = Field(..., min_length=1, max_length=500)

class GalleryItemCreate(GalleryItemBase):
    pass

class GalleryItemUpdate(GalleryItemBase):
    pass

class GalleryItem(GalleryItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Rule ---
class RuleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str

class RuleCreate(RuleBase):
    pass

class RuleUpdate(RuleBase):
    pass

class Rule(RuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Schedule ---
class Schedule(BaseModel):
    value: Optional[str] = None # Could be JSON string or other format

class ScheduleImage(BaseModel):
    imageUrl: str
