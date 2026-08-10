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
from models.target_list import TargetList
from models.target import Target
from routes.auth import router as auth_router
from routes.target_lists import router as target_lists_router
from utils.auth import hash_password


class BulkTargetEndpointTests(unittest.TestCase):
    """The frontend sends a wrapped JSON object, not a bare array, for both
    bulk endpoints (services/api/library/targetLists.js: bulkAddTargets and
    bulkDeleteTargets both do `JSON.stringify({ targets })` /
    `JSON.stringify({ target_ids })`). A bare `List[...]` body parameter
    without `Body(embed=True)` only accepts the raw array as the whole
    request body, so these endpoints silently rejected every real request
    from the browser with a 422."""

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
        app.include_router(target_lists_router, prefix="/api/target-lists")

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
            db.add(TargetList(id="list-1", name="Bulk Test List"))
            db.commit()

        response = self.client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.csrf_headers = {"X-CSRF-Token": response.json()["csrf_token"]}

    def test_bulk_add_accepts_the_wrapped_payload_the_frontend_sends(self):
        response = self.client.post(
            "/api/target-lists/list-1/targets/bulk",
            headers=self.csrf_headers,
            json={
                "targets": [
                    {"email": "john@example.com", "first_name": "John"},
                    {"email": "jane@example.com", "first_name": "Jane"},
                ]
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["created"], 2)
        self.assertEqual(body["skipped"], 0)

    def test_bulk_add_rejects_a_bare_array_body(self):
        response = self.client.post(
            "/api/target-lists/list-1/targets/bulk",
            headers=self.csrf_headers,
            json=[{"email": "john@example.com"}],
        )

        self.assertEqual(response.status_code, 422)

    def test_bulk_delete_accepts_the_wrapped_payload_the_frontend_sends(self):
        with self.Session() as db:
            db.add(
                Target(
                    id="target-1",
                    target_list_id="list-1",
                    email="john@example.com",
                )
            )
            db.commit()

        response = self.client.post(
            "/api/target-lists/list-1/targets/bulk-delete",
            headers=self.csrf_headers,
            json={"target_ids": ["target-1"]},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["deleted"], 1)


if __name__ == "__main__":
    unittest.main()
