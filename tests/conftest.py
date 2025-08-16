import os
import shutil
import pathlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from alembic import command
from alembic.config import Config

from app.main import app
from app.db import Base, get_db
from app.core.config import settings
from app.api.v1 import deps

# --- Choose DB for tests ---
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test.db")
IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")

# --- Create engine/session for tests ---
if IS_SQLITE:
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _fake_roles():
    return ["clinician", "admin"]

app.dependency_overrides[deps.get_current_user_roles] = _fake_roles

# --- Override the app's DB dependency ---
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
app.dependency_overrides[get_db] = override_get_db

# --- Storage: force a clean temp dir each run ---
@pytest.fixture(scope="session", autouse=True)
def _storage_tmpdir():
    root = pathlib.Path(os.getenv("FILE_STORAGE_DIR", "./var/test-uploads"))
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(root, ignore_errors=True)

# --- DB lifecycle per test session ---
@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    if IS_SQLITE:
        # Fast path: create/drop schema via metadata
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    else:
        # Neon (or any Postgres): run Alembic migrations to head
        cfg = Config("alembic.ini")
        # IMPORTANT: tell Alembic which DB URL to use
        cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
        command.upgrade(cfg, "head")
        yield
        # Optional: rollback after tests (often not needed on dedicated test DB)
        # command.downgrade(cfg, "base")

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session() -> Session:
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()
