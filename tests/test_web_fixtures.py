from __future__ import annotations

import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.models import Base
from app.database.repository import create_web_user
from app.web.dependencies import get_db_session
from app.web.main import app
from app.web.security import hash_password


class WebFixtureRoutesTest(unittest.TestCase):
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

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db_session] = override_db
        self.client = TestClient(app)
        self.client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_lists_leagues(self) -> None:
        response = self.client.get("/api/leagues")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(item["key"] == "premier_league" for item in response.json()))

    def test_lists_fixtures_from_mock_api_client(self) -> None:
        response = self.client.get("/api/fixtures?date=today&league_key=premier_league")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(len(payload["fixtures"]), 1)

    def test_analysis_payload_contains_dashboard_texts(self) -> None:
        response = self.client.get("/api/fixtures/101/analysis")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("advisor_text", payload)
        self.assertIn("dossier", payload)
        self.assertIn("player_advice_text", payload)
        self.assertIn("injuries_text", payload)


if __name__ == "__main__":
    unittest.main()
