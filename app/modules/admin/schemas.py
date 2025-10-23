
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserAdminOut(BaseModel):
    id: int
    name: str = Field(alias="nome")
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True  # allow using aliases

class InviteOut(BaseModel):
    id: int
    token: str
    email_hint: Optional[str] = None
    mentor_name_hint: Optional[str] = None
    created_by_user_id: int
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None
    used_by_user_id: Optional[int] = None

    class Config:
        from_attributes = True
