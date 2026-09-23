from collections.abc import Generator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from papermind.auth.dependencies import get_current_user
from papermind.auth.schemas import CurrentUser
from papermind.db.base import Base
from papermind.db.session import get_db
from papermind.main import create_app
from papermind.models import Folder, User


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

    async def override_current_user() -> CurrentUser:
        return CurrentUser(
            clerk_user_id="user_test123",
            email="promit@example.com",
            first_name="Promit",
            last_name="Saha",
            image_url=None,
        )

    def override_get_db() -> Generator[Session]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session


def sync_test_user(client: TestClient) -> str:
    response = client.get("/auth/me")
    assert response.status_code == 200
    return response.json()["id"]


def test_create_folder_creates_application_user_and_folder() -> None:
    client, testing_session = build_test_client()
    user_id = sync_test_user(client)

    response = client.post("/folders", json={"name": "Robotics Papers"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Robotics Papers"
    assert body["is_deleted"] is False
    assert body["id"]
    assert body["owner_id"] == user_id

    with testing_session() as session:
        user = session.scalar(select(User).where(User.clerk_user_id == "user_test123"))
        assert user is not None
        assert user.is_deleted is False
        assert user.email == "promit@example.com"

        folder = session.scalar(select(Folder).where(Folder.id == UUID(body["id"])))
        assert folder is not None
        assert folder.owner_id == user.id
        assert folder.name == "Robotics Papers"
        assert folder.is_deleted is False


def test_create_folder_reuses_existing_application_user() -> None:
    client, testing_session = build_test_client()
    sync_test_user(client)

    first_response = client.post("/folders", json={"name": "Folder One"})
    second_response = client.post("/folders", json={"name": "Folder Two"})

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_response.json()["owner_id"] == second_response.json()["owner_id"]

    with testing_session() as session:
        users = session.scalars(select(User)).all()
        folders = session.scalars(select(Folder)).all()

    assert len(users) == 1
    assert len(folders) == 2


def test_create_folder_requires_synced_application_user() -> None:
    client, _testing_session = build_test_client()

    response = client.post("/folders", json={"name": "Folder One"})

    assert response.status_code == 409


def test_create_folder_requires_authentication() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.post("/folders", json={"name": "Private Folder"})

    assert response.status_code == 401
