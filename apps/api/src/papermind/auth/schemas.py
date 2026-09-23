import uuid
from datetime import datetime

from pydantic import BaseModel


class CurrentUser(BaseModel):
    clerk_user_id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    image_url: str | None = None
    session_id: str | None = None
    organization_id: str | None = None
    organization_role: str | None = None


class UserRead(BaseModel):
    id: uuid.UUID
    clerk_user_id: str
    email: str
    first_name: str | None
    last_name: str | None
    image_url: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
