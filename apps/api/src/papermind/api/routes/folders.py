import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser
from papermind.db.session import get_db
from papermind.models import Folder
from papermind.schemas.folder import FolderCreate, FolderRead, FolderUpdate
from papermind.services.users import get_user_for_current_auth

router = APIRouter()


@router.get("", response_model=list[FolderRead])
def list_folders(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> list[Folder]:
    user = get_user_for_current_auth(session, current_user)
    return list(
        session.scalars(
            select(Folder)
            .where(
                Folder.owner_id == user.id,
                Folder.is_deleted.is_(False),
            )
            .order_by(Folder.created_at.desc())
        )
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


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(
    folder_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> Folder:
    user = get_user_for_current_auth(session, current_user)
    return get_owned_folder(session, folder_id, user.id)


@router.patch("/{folder_id}", response_model=FolderRead)
def update_folder(
    folder_id: uuid.UUID,
    payload: FolderUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> Folder:
    user = get_user_for_current_auth(session, current_user)
    folder = get_owned_folder(session, folder_id, user.id)
    folder.name = payload.name.strip()
    session.commit()
    session.refresh(folder)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: uuid.UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> None:
    user = get_user_for_current_auth(session, current_user)
    folder = get_owned_folder(session, folder_id, user.id)
    folder.is_deleted = True
    session.commit()


def get_owned_folder(
    session: Session,
    folder_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Folder:
    folder = session.scalar(
        select(Folder).where(
            Folder.id == folder_id,
            Folder.owner_id == owner_id,
            Folder.is_deleted.is_(False),
        )
    )
    if folder is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found.",
        )
    return folder
