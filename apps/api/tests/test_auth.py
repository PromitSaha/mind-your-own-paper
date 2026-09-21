from fastapi.testclient import TestClient

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser
from papermind.main import create_app


def test_auth_me_requires_authentication() -> None:
    client = TestClient(create_app())

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_me_returns_current_user_from_dependency() -> None:
    app = create_app()

    async def override_current_user() -> CurrentUser:
        return CurrentUser(
            clerk_user_id="user_test123",
            session_id="sess_test123",
            organization_id=None,
            organization_role=None,
        )

    app.dependency_overrides[get_current_user] = override_current_user
    client = TestClient(app)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "clerk_user_id": "user_test123",
        "session_id": "sess_test123",
        "organization_id": None,
        "organization_role": None,
    }
