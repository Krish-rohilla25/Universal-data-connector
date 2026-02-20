"""
Tests for the three data connectors.

We test each connector in isolation – no HTTP layer involved.  We verify
that filters work correctly and that results are in the expected order.
"""

import pytest
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector


class TestCRMConnector:
    """Unit tests for CRMConnector.fetch()"""

    def setup_method(self):
        self.connector = CRMConnector()

    def test_fetch_returns_list(self):
        results = self.connector.fetch()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_filter_by_status(self):
        results = self.connector.fetch(status="active")
        assert all(r["status"] == "active" for r in results)

    def test_filter_by_unknown_status_returns_empty(self):
        results = self.connector.fetch(status="deleted")
        assert results == []

    def test_filter_by_plan(self):
        """If any plan field exists in data, filtering by it should work."""
        all_records = self.connector.fetch()
        plans = {r.get("plan") for r in all_records if r.get("plan")}
        if plans:
            plan = next(iter(plans))
            results = self.connector.fetch(plan=plan)
            assert all(r.get("plan") == plan for r in results)

    def test_name_search_case_insensitive(self):
        all_records = self.connector.fetch()
        if all_records:
            # Grab the first letter of the first customer's name
            first_letter = all_records[0]["name"][0].upper()
            results = self.connector.fetch(name_search=first_letter.lower())
            assert len(results) >= 1
            assert all(first_letter.lower() in r["name"].lower() for r in results)

    def test_sort_desc(self):
        results = self.connector.fetch(sort_by="created_at", sort_desc=True)
        dates = [r["created_at"] for r in results]
        assert dates == sorted(dates, reverse=True)

    def test_llm_schema_has_required_keys(self):
        schema = self.connector.llm_schema()
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
        assert schema["name"] == "get_crm_customers"


class TestSupportConnector:
    """Unit tests for SupportConnector.fetch()"""

    def setup_method(self):
        self.connector = SupportConnector()

    def test_fetch_returns_list(self):
        results = self.connector.fetch()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_filter_by_status_open(self):
        results = self.connector.fetch(status="open")
        assert all(r["status"] == "open" for r in results)

    def test_filter_by_priority_high(self):
        results = self.connector.fetch(priority="high")
        assert all(r["priority"] == "high" for r in results)

    def test_filter_by_customer_id(self):
        all_records = self.connector.fetch()
        if all_records:
            cid = all_records[0]["customer_id"]
            results = self.connector.fetch(customer_id=cid)
            assert all(r["customer_id"] == cid for r in results)

    def test_combined_filter(self):
        results = self.connector.fetch(status="open", priority="high")
        assert all(r["status"] == "open" and r["priority"] == "high" for r in results)

    def test_llm_schema_function_name(self):
        schema = self.connector.llm_schema()
        assert schema["name"] == "get_support_tickets"


class TestAnalyticsConnector:
    """Unit tests for AnalyticsConnector.fetch()"""

    def setup_method(self):
        self.connector = AnalyticsConnector()

    def test_fetch_returns_list(self):
        results = self.connector.fetch()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_filter_by_metric(self):
        results = self.connector.fetch(metric="daily_active_users")
        assert all(r["metric"] == "daily_active_users" for r in results)

    def test_aggregate_returns_single_record(self):
        results = self.connector.fetch(metric="daily_active_users", aggregate=True)
        assert len(results) == 1
        summary = results[0]
        assert "average" in summary
        assert "minimum" in summary
        assert "maximum" in summary
        assert summary["_aggregated"] is True

    def test_aggregate_average_within_range(self):
        results = self.connector.fetch(metric="daily_active_users", aggregate=True)
        summary = results[0]
        assert summary["minimum"] <= summary["average"] <= summary["maximum"]

    def test_date_filter(self):
        all_records = self.connector.fetch(metric="daily_active_users")
        if len(all_records) >= 2:
            # Use the date of the second record as a cutoff
            cutoff = all_records[-1]["date"]
            results = self.connector.fetch(metric="daily_active_users", date_from=cutoff)
            assert all(r["date"] >= cutoff for r in results)

    def test_llm_schema_function_name(self):
        schema = self.connector.llm_schema()
        assert schema["name"] == "get_analytics_metrics"
