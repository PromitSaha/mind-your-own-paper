from pydantic import BaseModel


class CurrentUser(BaseModel):
    clerk_user_id: str
    session_id: str | None = None
    organization_id: str | None = None
    organization_role: str | None = None
