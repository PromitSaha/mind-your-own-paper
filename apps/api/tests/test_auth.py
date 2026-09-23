from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser
from papermind.db.base import Base
from papermind.db.session import get_db
from papermind.main import create_app
from papermind.models import User


def build_test_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    app = create_app()

    def override_get_db() -> Generator[Session]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def test_auth_me_requires_authentication() -> None:
    client = TestClient(create_app())

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_auth_me_syncs_application_user_from_auth_identity() -> None:
    client, testing_session = build_test_client()

    async def override_current_user() -> CurrentUser:
        return CurrentUser(
            clerk_user_id="user_test123",
            email="promit@example.com",
            first_name="Promit",
            last_name="Saha",
            image_url="https://example.com/avatar.png",
            session_id="sess_test123",
            organization_id=None,
            organization_role=None,
        )

    app = client.app
    app.dependency_overrides[get_current_user] = override_current_user

    response = client.get("/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": body["id"],
        "clerk_user_id": "user_test123",
        "email": "promit@example.com",
        "first_name": "Promit",
        "last_name": "Saha",
        "image_url": "https://example.com/avatar.png",
        "is_deleted": False,
        "created_at": body["created_at"],
        "updated_at": body["updated_at"],
    }

    with testing_session() as session:
        user = session.scalar(select(User).where(User.email == "promit@example.com"))

    assert user is not None
    assert user.clerk_user_id == "user_test123"
    assert user.first_name == "Promit"


def test_auth_me_reuses_existing_user_by_email() -> None:
    client, testing_session = build_test_client()

    with testing_session() as session:
        existing_user = User(
            clerk_user_id="old_clerk_id",
            email="promit@example.com",
            first_name="Old",
            last_name=None,
            image_url=None,
        )
        session.add(existing_user)
        session.commit()
        existing_user_id = existing_user.id

    async def override_current_user() -> CurrentUser:
        return CurrentUser(
            clerk_user_id="new_clerk_id",
            email="promit@example.com",
            first_name="Promit",
            last_name="Saha",
            image_url=None,
        )

    app = client.app
    app.dependency_overrides[get_current_user] = override_current_user

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(existing_user_id)

    with testing_session() as session:
        users = session.scalars(select(User)).all()

    assert len(users) == 1
    assert users[0].clerk_user_id == "new_clerk_id"
    assert users[0].email == "promit@example.com"
