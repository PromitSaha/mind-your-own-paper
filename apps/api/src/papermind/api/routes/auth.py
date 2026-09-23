from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser, UserRead
from papermind.db.session import get_db
from papermind.services.users import sync_user_from_auth

router = APIRouter()


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> UserRead:
    user = sync_user_from_auth(session, current_user)
    return UserRead.model_validate(user, from_attributes=True)
