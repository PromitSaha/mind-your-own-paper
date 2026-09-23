from sqlalchemy import select
from sqlalchemy.orm import Session

from papermind.auth.schemas import CurrentUser
from papermind.models import User


def sync_user_from_auth(session: Session, current_user: CurrentUser) -> User:
    user = session.scalar(
        select(User).where(User.clerk_user_id == current_user.clerk_user_id)
    )

    if user is None:
        user = session.scalar(select(User).where(User.email == current_user.email))

    if user is None:
        user = User(
            clerk_user_id=current_user.clerk_user_id,
            email=current_user.email,
        )
        session.add(user)

    user.clerk_user_id = current_user.clerk_user_id
    user.email = current_user.email
    user.first_name = current_user.first_name
    user.last_name = current_user.last_name
    user.image_url = current_user.image_url

    session.commit()
    session.refresh(user)
    return user
