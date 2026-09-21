from typing import Annotated

from fastapi import APIRouter, Depends

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser

router = APIRouter()


@router.get("/me", response_model=CurrentUser)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    return current_user
