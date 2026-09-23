from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser
from papermind.db.session import get_db
from papermind.models import Folder, User
from papermind.schemas.folder import FolderCreate, FolderRead

router = APIRouter()


def get_user_for_current_auth(session: Session, current_user: CurrentUser) -> User:
    user = session.scalar(
        select(User).where(
            User.clerk_user_id == current_user.clerk_user_id,
            User.is_deleted.is_(False),
        )
    )
    if user is not None:
        return user

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "User profile has not been synced. "
            "Call /auth/me before creating folders."
        ),
    )


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: FolderCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> Folder:
    user = get_user_for_current_auth(session, current_user)
    folder = Folder(owner_id=user.id, name=payload.name.strip())
    session.add(folder)
    session.commit()
    session.refresh(folder)
    return folder
