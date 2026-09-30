from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from papermind.db.base import Base
from papermind.models import File, FileStatus, Folder, User


def build_session() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_new_file_defaults_to_pending_upload() -> None:
    testing_session = build_session()

    with testing_session() as session:
        user = User(
            clerk_user_id="user_test123",
            email="promit@example.com",
        )
        folder = Folder(name="Robotics Papers", owner=user)
        file = File(
            folder=folder,
            original_filename="paper.pdf",
            s3_bucket="papermind-dev-8086",
            s3_key="folders/folder-id/files/file-id/original.pdf",
            content_type="application/pdf",
            size_bytes=1024,
        )

        session.add(file)
        session.flush()

        assert file.status == FileStatus.PENDING_UPLOAD
