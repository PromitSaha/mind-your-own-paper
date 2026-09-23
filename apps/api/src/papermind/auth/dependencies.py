from typing import Annotated

from clerk_backend_api import AuthenticateRequestOptions, Clerk
from fastapi import Depends, HTTPException, Request, status

from papermind.auth.schemas import CurrentUser
from papermind.core.config import Settings, get_settings


def _build_clerk_client(settings: Settings) -> Clerk:
    return Clerk(bearer_auth=settings.clerk_secret_key)


def _get_primary_email(clerk_user: object) -> str | None:
    primary_email_address_id = getattr(clerk_user, "primary_email_address_id", None)
    email_addresses = getattr(clerk_user, "email_addresses", [])

    for email_address in email_addresses:
        if getattr(email_address, "id", None) == primary_email_address_id:
            return getattr(email_address, "email_address", None)

    if email_addresses:
        return getattr(email_addresses[0], "email_address", None)

    return None


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

    clerk_user = await clerk_client.users.get_async(user_id=user_id)
    email = _get_primary_email(clerk_user)
    if not isinstance(email, str) or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated Clerk user is missing an email address.",
        )

    return CurrentUser(
        clerk_user_id=user_id,
        email=email,
        first_name=getattr(clerk_user, "first_name", None),
        last_name=getattr(clerk_user, "last_name", None),
        image_url=getattr(clerk_user, "image_url", None),
        session_id=request_state.payload.get("sid"),
        organization_id=request_state.payload.get("org_id"),
        organization_role=request_state.payload.get("org_role"),
    )
