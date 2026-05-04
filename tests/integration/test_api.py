"""
OpsSwarm — Integration Test: API Health Endpoints
====================================================
Tests the FastAPI health and readiness endpoints using the async test client.
Requires no external services (DB/Redis/Qdrant not needed).
"""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app():
    from api.main import app
    return app


@pytest.mark.asyncio
class TestHealthEndpoints:
    async def test_health_returns_200(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_response_schema(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        body = response.json()
        assert body["status"] == "ok"
        assert body["app"] == "OpsSwarm"
        assert "version" in body
        assert "timestamp" in body

    async def test_readiness_returns_200(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ready")
        assert response.status_code == 200

    async def test_readiness_has_api_check(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ready")
        body = response.json()
        assert "checks" in body
        assert body["checks"]["api"] == "ok"


@pytest.mark.asyncio
class TestIncidentEndpoints:
    async def test_ingest_alert_returns_202(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/incidents/ingest", json={
                "service": "auth-service",
                "severity": "CRITICAL",
                "event_type": "brute_force_attack",
                "message": "847 failed logins in 3 minutes",
            })
        assert response.status_code == 202

    async def test_ingest_returns_incident_id(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/incidents/ingest", json={
                "service": "db-primary",
                "severity": "HIGH",
                "event_type": "db_pool_exhausted",
                "message": "Pool at 98%",
            })
        body = response.json()
        assert "incident_id" in body
        assert body["incident_id"].startswith("INC-")
        assert "correlation_id" in body

    async def test_list_incidents_returns_list(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/incidents")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_known_incident(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/incidents/INC-A1B2C3D4")
        assert response.status_code == 200
        assert response.json()["incident_id"] == "INC-A1B2C3D4"

    async def test_get_unknown_incident_returns_404(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/incidents/INC-DOESNOTEXIST")
        assert response.status_code == 404

    async def test_correlation_id_in_response_headers(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        assert "x-correlation-id" in response.headers
