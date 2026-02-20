"""
Tests for the business rules and voice optimizer services.
"""

import pytest
from app.services.business_rules import apply_voice_limits, prioritise_support_tickets, get_freshness_label
from app.services.voice_optimizer import build_voice_summary
from app.services.data_identifier import identify_data_type


class TestApplyVoiceLimits:
    """Tests for apply_voice_limits()"""

    def _make_records(self, count: int):
        return [{"id": i} for i in range(count)]

    def test_respects_limit(self):
        records = self._make_records(50)
        result = apply_voice_limits(records, limit=5)
        assert len(result) == 5

    def test_voice_mode_uses_tighter_cap(self):
        records = self._make_records(50)
        # voice mode should return fewer items than default API mode
        voice_result = apply_voice_limits(records, voice_mode=True)
        api_result = apply_voice_limits(records, voice_mode=False)
        assert len(voice_result) <= len(api_result)

    def test_does_not_exceed_records_count(self):
        records = self._make_records(3)
        result = apply_voice_limits(records, limit=10)
        assert len(result) == 3

    def test_empty_list(self):
        result = apply_voice_limits([])
        assert result == []


class TestPrioritiseSupportTickets:
    """Tests for prioritise_support_tickets()"""

    def test_open_high_priority_first(self):
        records = [
            {"ticket_id": 1, "status": "closed", "priority": "high"},
            {"ticket_id": 2, "status": "open", "priority": "low"},
            {"ticket_id": 3, "status": "open", "priority": "high"},
        ]
        result = prioritise_support_tickets(records)
        # First record should be open+high
        assert result[0]["ticket_id"] == 3

    def test_closed_tickets_go_last(self):
        records = [
            {"ticket_id": 1, "status": "closed", "priority": "high"},
            {"ticket_id": 2, "status": "open", "priority": "low"},
        ]
        result = prioritise_support_tickets(records)
        assert result[-1]["status"] == "closed"

    def test_returns_same_count(self):
        records = [{"ticket_id": i, "status": "open", "priority": "medium"} for i in range(10)]
        result = prioritise_support_tickets(records)
        assert len(result) == 10


class TestGetFreshnessLabel:
    """Tests for get_freshness_label()"""

    def test_returns_string(self):
        label = get_freshness_label()
        assert isinstance(label, str)
        assert "Data as of" in label


class TestIdentifyDataType:
    """Tests for identify_data_type()"""

    def test_empty_list(self):
        assert identify_data_type([]) == "empty"

    def test_crm_type(self):
        records = [{"customer_id": 1, "name": "Alice", "status": "active"}]
        assert identify_data_type(records) == "tabular_crm"

    def test_support_type(self):
        records = [{"ticket_id": 1, "subject": "Bug", "priority": "high"}]
        assert identify_data_type(records) == "tabular_support"

    def test_time_series_type(self):
        records = [{"metric": "daily_active_users", "date": "2026-01-01", "value": 500}]
        assert identify_data_type(records) == "time_series"

    def test_aggregated_type(self):
        records = [{"metric": "daily_active_users", "average": 500, "_aggregated": True}]
        assert identify_data_type(records) == "aggregated"

    def test_unknown_type(self):
        records = [{"foo": "bar", "baz": 42}]
        assert identify_data_type(records) == "unknown"


class TestBuildVoiceSummary:
    """Tests for build_voice_summary()"""

    def test_crm_summary_all(self):
        summary = build_voice_summary("crm", "tabular_crm", 10, 10, {})
        assert "10" in summary
        assert "customer" in summary.lower()

    def test_crm_summary_partial(self):
        summary = build_voice_summary("crm", "tabular_crm", 5, 23, {"status": "active"})
        assert "5" in summary
        assert "23" in summary

    def test_support_summary_open(self):
        summary = build_voice_summary("support", "tabular_support", 3, 12, {"status": "open", "priority": "high"})
        assert "open" in summary
        assert "high" in summary

    def test_analytics_aggregate_summary(self):
        summary = build_voice_summary("analytics", "aggregated", 1, 1, {})
        assert "aggregated" in summary.lower() or "summary" in summary.lower()

    def test_returns_string(self):
        summary = build_voice_summary("analytics", "time_series", 7, 30, {})
        assert isinstance(summary, str)
        assert len(summary) > 0
