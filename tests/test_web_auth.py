from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import Base
from app.database.repository import create_web_user
from app.web.dependencies import get_db_session
from app.web.main import app, login_limiter
from app.web.security import hash_password


class WebAuthTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine, future=True)

        with self.Session() as db:
            create_web_user(
                db,
                email="admin@example.com",
                password_hash=hash_password("secret123"),
                role="admin",
            )
            create_web_user(
                db,
                email="user@example.com",
                password_hash=hash_password("secret123"),
                role="user",
            )

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db_session] = override_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        login_limiter.clear()

    def test_protected_route_requires_session_cookie(self) -> None:
        response = self.client.get("/api/me")

        self.assertEqual(response.status_code, 401)

    def test_login_me_and_logout_flow(self) -> None:
        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "secret123"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["email"], "admin@example.com")

        me_response = self.client.get("/api/me")
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["role"], "admin")

        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)

    def test_login_rate_limit_blocks_repeated_failures(self) -> None:
        for _ in range(5):
            response = self.client.post(
                "/api/auth/login",
                json={"email": "admin@example.com", "password": "wrong-password"},
            )
            self.assertEqual(response.status_code, 401)

        blocked = self.client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "wrong-password"},
        )
        self.assertEqual(blocked.status_code, 429)

    def test_admin_can_create_user_and_change_password(self) -> None:
        self.client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})

        create_response = self.client.post(
            "/api/admin/users",
            json={"email": "new-user@example.com", "password": "initial123"},
        )
        self.assertEqual(create_response.status_code, 201)
        created = create_response.json()
        self.assertEqual(created["role"], "user")

        password_response = self.client.put(
            f"/api/admin/users/{created['id']}/password",
            json={"password": "changed123"},
        )
        self.assertEqual(password_response.status_code, 200)

        self.client.post("/api/auth/logout")
        login_response = self.client.post(
            "/api/auth/login",
            json={"email": "new-user@example.com", "password": "changed123"},
        )
        self.assertEqual(login_response.status_code, 200)

    def test_common_user_cannot_manage_users(self) -> None:
        self.client.post("/api/auth/login", json={"email": "user@example.com", "password": "secret123"})

        response = self.client.get("/api/admin/users")

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
