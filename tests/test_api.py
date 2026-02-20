"""
Integration tests for the FastAPI HTTP endpoints.

We use httpx.TestClient (via starlette's test client) to send HTTP requests
to the app in-process.  No network is involved – this is fast and reliable.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Tests for /health/* routes"""

    def test_health_ok(self):
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_health_info(self):
        response = client.get("/health/info")
        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "max_results" in data


class TestCRMEndpoints:
    """Tests for GET /data/crm"""

    def test_get_crm_default(self):
        response = client.get("/data/crm")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "metadata" in body
        assert len(body["data"]) <= 10

    def test_get_crm_filter_active(self):
        response = client.get("/data/crm?status=active")
        assert response.status_code == 200
        body = response.json()
        for record in body["data"]:
            assert record["status"] == "active"

    def test_get_crm_limit_applied(self):
        response = client.get("/data/crm?limit=3")
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) <= 3

    def test_get_crm_voice_mode(self):
        response = client.get("/data/crm?voice_mode=true")
        assert response.status_code == 200
        body = response.json()
        # Voice mode should return fewer records
        assert len(body["data"]) <= 5

    def test_crm_metadata_fields(self):
        response = client.get("/data/crm")
        meta = response.json()["metadata"]
        assert "source" in meta
        assert "voice_summary" in meta
        assert "data_freshness" in meta
        assert "pagination" in meta
        assert meta["source"] == "crm"

    def test_crm_voice_summary_is_string(self):
        response = client.get("/data/crm")
        summary = response.json()["metadata"]["voice_summary"]
        assert isinstance(summary, str)
        assert len(summary) > 0


class TestSupportEndpoints:
    """Tests for GET /data/support"""

    def test_get_support_default(self):
        response = client.get("/data/support")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert len(body["data"]) <= 10

    def test_get_support_filter_open(self):
        response = client.get("/data/support?status=open")
        assert response.status_code == 200
        for record in response.json()["data"]:
            assert record["status"] == "open"

    def test_get_support_filter_high_priority(self):
        response = client.get("/data/support?priority=high")
        assert response.status_code == 200
        for record in response.json()["data"]:
            assert record["priority"] == "high"

    def test_support_metadata_source(self):
        meta = client.get("/data/support").json()["metadata"]
        assert meta["source"] == "support"

    def test_support_pagination_has_more(self):
        response = client.get("/data/support?limit=1")
        pagination = response.json()["metadata"]["pagination"]
        assert pagination["returned_records"] == 1
        # There are 50 records in the fixture so has_more should be True
        assert pagination["total_records"] > 1
        assert pagination["has_more"] is True


class TestAnalyticsEndpoints:
    """Tests for GET /data/analytics"""

    def test_get_analytics_default(self):
        response = client.get("/data/analytics")
        assert response.status_code == 200
        body = response.json()
        assert "data" in body

    def test_get_analytics_filter_metric(self):
        response = client.get("/data/analytics?metric=daily_active_users")
        assert response.status_code == 200
        for record in response.json()["data"]:
            assert record["metric"] == "daily_active_users"

    def test_get_analytics_aggregate(self):
        response = client.get("/data/analytics?metric=daily_active_users&aggregate=true")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert "average" in data[0]
        assert "minimum" in data[0]
        assert "maximum" in data[0]

    def test_analytics_metadata_source(self):
        meta = client.get("/data/analytics").json()["metadata"]
        assert meta["source"] == "analytics"


class TestGenericDataEndpoint:
    """Tests for the legacy GET /data/{source} route"""

    def test_valid_source_crm(self):
        response = client.get("/data/crm")
        assert response.status_code == 200

    def test_invalid_source_returns_404(self):
        response = client.get("/data/billing")
        # The named routes won't match 'billing', and the generic route returns 404
        assert response.status_code == 404


class TestLLMEndpoints:
    """Tests for /llm/* routes"""

    def test_list_functions_returns_schemas(self):
        response = client.get("/llm/functions")
        assert response.status_code == 200
        body = response.json()
        assert "functions" in body
        assert len(body["functions"]) == 3
        names = {f["name"] for f in body["functions"]}
        assert "get_crm_customers" in names
        assert "get_support_tickets" in names
        assert "get_analytics_metrics" in names

    def test_llm_call_crm(self):
        payload = {
            "function_name": "get_crm_customers",
            "arguments": {"status": "active"},
        }
        response = client.post("/llm/call", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "metadata" in body
        for record in body["data"]:
            assert record["status"] == "active"

    def test_llm_call_support(self):
        payload = {
            "function_name": "get_support_tickets",
            "arguments": {"priority": "high"},
        }
        response = client.post("/llm/call", json=payload)
        assert response.status_code == 200
        for record in response.json()["data"]:
            assert record["priority"] == "high"

    def test_llm_call_analytics_aggregate(self):
        payload = {
            "function_name": "get_analytics_metrics",
            "arguments": {"metric": "daily_active_users", "aggregate": True},
        }
        response = client.post("/llm/call", json=payload)
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data) == 1
        assert "average" in data[0]

    def test_llm_call_unknown_function(self):
        payload = {
            "function_name": "get_billing_data",
            "arguments": {},
        }
        response = client.post("/llm/call", json=payload)
        assert response.status_code == 400
        assert "Unknown function" in response.json()["detail"]

    def test_llm_response_has_voice_summary(self):
        payload = {"function_name": "get_crm_customers", "arguments": {}}
        response = client.post("/llm/call", json=payload)
        summary = response.json()["metadata"]["voice_summary"]
        assert isinstance(summary, str)
        assert len(summary) > 10
