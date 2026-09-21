from typing import Annotated

from clerk_backend_api import AuthenticateRequestOptions, Clerk
from fastapi import Depends, HTTPException, Request, status

from papermind.auth.schemas import CurrentUser
from papermind.core.config import Settings, get_settings


def _build_clerk_client(settings: Settings) -> Clerk:
    return Clerk(bearer_auth=settings.clerk_secret_key)


async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    clerk_client = _build_clerk_client(settings)
    request_state = await clerk_client.authenticate_request_async(
        request,
        AuthenticateRequestOptions(
            secret_key=settings.clerk_secret_key,
            jwt_key=settings.clerk_jwt_key,
            authorized_parties=settings.clerk_authorized_parties_list,
        ),
    )

    if not request_state.is_authenticated or request_state.payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=request_state.message or "Authentication required.",
        )

    user_id = request_state.payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated Clerk token is missing a user id.",
        )

    return CurrentUser(
        clerk_user_id=user_id,
        session_id=request_state.payload.get("sid"),
        organization_id=request_state.payload.get("org_id"),
        organization_role=request_state.payload.get("org_role"),
    )
