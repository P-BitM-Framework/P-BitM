import os
import unittest

os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key-" + ("x" * 32))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models  # noqa: F401 - register all ORM models before creating the schema
from database import Base, get_db
from models.user import User
from models.user_session import UserSession
from routes.auth import router as auth_router
from utils.auth import hash_password
from utils.session_auth import SESSION_COOKIE_NAME, hash_secret


class WebSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.Session = sessionmaker(
            bind=cls.engine,
            autocommit=False,
            autoflush=False,
        )

        app = FastAPI()
        app.include_router(auth_router, prefix="/api/auth")

        def override_db():
            db = cls.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        cls.client = TestClient(app, base_url="https://testserver")

    def setUp(self):
        self.client.cookies.clear()
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        with self.Session() as db:
            db.add(
                User(
                    id="admin-1",
                    username="admin",
                    email="admin@example.test",
                    password=hash_password("correct horse battery staple"),
                    role="admin",
                    is_active=True,
                )
            )
            db.commit()

    def login(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def test_login_cookie_is_secure_httponly_and_strict(self):
        response = self.login()
        cookie = response.headers["set-cookie"]

        self.assertIn(f"{SESSION_COOKIE_NAME}=", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=strict", cookie)
        self.assertIn("Path=/", cookie)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_only_session_and_csrf_hashes_are_stored(self):
        response = self.login()
        raw_session = self.client.cookies.get(SESSION_COOKIE_NAME)
        raw_csrf = response.json()["csrf_token"]

        with self.Session() as db:
            session = db.query(UserSession).one()
            self.assertNotEqual(session.token_hash, raw_session)
            self.assertNotEqual(session.csrf_hash, raw_csrf)
            self.assertEqual(session.token_hash, hash_secret(raw_session))
            self.assertEqual(session.csrf_hash, hash_secret(raw_csrf))

    def test_me_restores_identity_and_rotates_csrf_token(self):
        login_response = self.login()
        old_csrf = login_response.json()["csrf_token"]

        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["username"], "admin")
        self.assertNotEqual(response.json()["csrf_token"], old_csrf)
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_unsafe_request_requires_current_csrf_token(self):
        login_response = self.login()
        old_csrf = login_response.json()["csrf_token"]
        me_response = self.client.get("/api/auth/me")
        current_csrf = me_response.json()["csrf_token"]

        missing = self.client.post("/api/auth/logout")
        self.assertEqual(missing.status_code, 403)

        stale = self.client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": old_csrf},
        )
        self.assertEqual(stale.status_code, 403)

        valid = self.client.post(
            "/api/auth/logout",
            headers={"X-CSRF-Token": current_csrf},
        )
        self.assertEqual(valid.status_code, 200, valid.text)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_expired_session_is_rejected_and_deleted(self):
        from datetime import datetime, timedelta, timezone

        self.login()
        with self.Session() as db:
            session = db.query(UserSession).one()
            session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()

        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        with self.Session() as db:
            self.assertEqual(db.query(UserSession).count(), 0)


if __name__ == "__main__":
    unittest.main()
