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


def test_list_folders_returns_owned_non_deleted_folders() -> None:
    client, testing_session = build_test_client()
    user_id = sync_test_user(client)

    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        owned_folder = Folder(owner_id=UUID(user_id), name="Owned Folder")
        deleted_folder = Folder(
            owner_id=UUID(user_id),
            name="Deleted Folder",
            is_deleted=True,
        )
        other_folder = Folder(owner=other_user, name="Other Folder")
        session.add_all([owned_folder, deleted_folder, other_folder])
        session.commit()
        owned_folder_id = owned_folder.id

    response = client.get("/folders")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(owned_folder_id),
            "owner_id": user_id,
            "name": "Owned Folder",
            "is_deleted": False,
            "created_at": response.json()[0]["created_at"],
            "updated_at": response.json()[0]["updated_at"],
        }
    ]


def test_get_folder_returns_owned_folder() -> None:
    client, testing_session = build_test_client()
    user_id = sync_test_user(client)

    with testing_session() as session:
        folder = Folder(owner_id=UUID(user_id), name="Owned Folder")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.get(f"/folders/{folder_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(folder_id)
    assert response.json()["name"] == "Owned Folder"


def test_get_folder_rejects_deleted_folder() -> None:
    client, testing_session = build_test_client()
    user_id = sync_test_user(client)

    with testing_session() as session:
        folder = Folder(
            owner_id=UUID(user_id),
            name="Deleted Folder",
            is_deleted=True,
        )
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.get(f"/folders/{folder_id}")

    assert response.status_code == 404


def test_get_folder_rejects_another_users_folder() -> None:
    client, testing_session = build_test_client()
    sync_test_user(client)

    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        folder = Folder(owner=other_user, name="Private Folder")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.get(f"/folders/{folder_id}")

    assert response.status_code == 404


def test_update_folder_renames_owned_folder() -> None:
    client, testing_session = build_test_client()
    user_id = sync_test_user(client)

    with testing_session() as session:
        folder = Folder(owner_id=UUID(user_id), name="Old Name")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.patch(f"/folders/{folder_id}", json={"name": "New Name"})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(folder_id)
    assert body["name"] == "New Name"
    assert body["is_deleted"] is False

    with testing_session() as session:
        folder = session.get(Folder, folder_id)

    assert folder is not None
    assert folder.name == "New Name"


def test_update_folder_rejects_another_users_folder() -> None:
    client, testing_session = build_test_client()
    sync_test_user(client)

    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        folder = Folder(owner=other_user, name="Private Folder")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.patch(f"/folders/{folder_id}", json={"name": "New Name"})

    assert response.status_code == 404


def test_delete_folder_soft_deletes_owned_folder() -> None:
    client, testing_session = build_test_client()
    user_id = sync_test_user(client)

    with testing_session() as session:
        folder = Folder(owner_id=UUID(user_id), name="Folder")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.delete(f"/folders/{folder_id}")

    assert response.status_code == 204
    assert response.content == b""

    with testing_session() as session:
        folder = session.get(Folder, folder_id)

    assert folder is not None
    assert folder.is_deleted is True


def test_delete_folder_rejects_already_deleted_folder() -> None:
    client, testing_session = build_test_client()
    user_id = sync_test_user(client)

    with testing_session() as session:
        folder = Folder(
            owner_id=UUID(user_id),
            name="Folder",
            is_deleted=True,
        )
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.delete(f"/folders/{folder_id}")

    assert response.status_code == 404


def test_delete_folder_rejects_another_users_folder() -> None:
    client, testing_session = build_test_client()
    sync_test_user(client)

    with testing_session() as session:
        other_user = User(
            clerk_user_id="other_user",
            email="other@example.com",
        )
        folder = Folder(owner=other_user, name="Private Folder")
        session.add(folder)
        session.commit()
        folder_id = folder.id

    response = client.delete(f"/folders/{folder_id}")

    assert response.status_code == 404
