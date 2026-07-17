"""
DB/LLM-free unit tests for the application financing fields (migration 004).

Tests cover:
- ApplicationFinancing model validation
- CreateApplicationRequest accepts all four new fields
- BankApplicationListItem and BankApplicationDetail include `amount`
- ApplicationStatus Literal matches the live DB enum exactly
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import ApplicationFinancing, ApplicationStatus
from routers.applications import CreateApplicationRequest
from routers.bank import BankApplicationDetail, BankApplicationListItem


# ---------------------------------------------------------------------------
# ApplicationFinancing model
# ---------------------------------------------------------------------------

class TestApplicationFinancing:
    def test_all_optional(self):
        f = ApplicationFinancing()
        assert f.amount is None
        assert f.purpose is None
        assert f.term_months is None
        assert f.description is None

    def test_full_payload(self):
        f = ApplicationFinancing(
            amount=500_000.0,
            purpose="Equipment purchase",
            term_months=36,
            description="Expanding our fleet of delivery vehicles.",
        )
        assert f.amount == 500_000.0
        assert f.term_months == 36

    def test_amount_accepts_float(self):
        f = ApplicationFinancing(amount=123456.78)
        assert f.amount == pytest.approx(123456.78)


# ---------------------------------------------------------------------------
# CreateApplicationRequest — includes financing fields
# ---------------------------------------------------------------------------

class TestCreateApplicationRequest:
    def test_empty_body_valid(self):
        req = CreateApplicationRequest()
        assert req.requested_amount is None
        assert req.amount is None
        assert req.purpose is None
        assert req.term_months is None
        assert req.description is None

    def test_full_financing_body(self):
        req = CreateApplicationRequest(
            requested_amount=400_000.0,
            amount=400_000.0,
            purpose="Working capital",
            term_months=24,
            description="Seasonal inventory build-up for Ramadan.",
        )
        assert req.amount == 400_000.0
        assert req.term_months == 24

    def test_financing_fields_independent_of_requested_amount(self):
        req = CreateApplicationRequest(amount=200_000.0)
        assert req.requested_amount is None
        assert req.amount == 200_000.0


# ---------------------------------------------------------------------------
# Bank response models include amount
# ---------------------------------------------------------------------------

class TestBankListItemAmount:
    def test_amount_field_exists_and_optional(self):
        item = BankApplicationListItem(
            application_id="app-1",
            sme_name="Test Co",
            sector="retail",
            district="Riyadh",
            submitted_at="2026-07-16T10:00:00",
            forensic_status=None,
            business_model_score=None,
        )
        assert item.amount is None

    def test_amount_surfaced(self):
        item = BankApplicationListItem(
            application_id="app-1",
            sme_name="Test Co",
            sector="retail",
            district="Riyadh",
            submitted_at="2026-07-16T10:00:00",
            forensic_status="green",
            business_model_score=72,
            amount=350_000.0,
        )
        assert item.amount == 350_000.0


# ---------------------------------------------------------------------------
# ApplicationStatus — matches live DB enum (no "submitted", no "info_requested")
# ---------------------------------------------------------------------------

class TestApplicationStatusEnum:
    _LIVE_DB_VALUES = {
        "draft",
        "processing",
        "review_ready",
        "approved",
        "rejected",
        "more_info_needed",
    }
    _REMOVED_VALUES = {"submitted", "info_requested"}

    def test_valid_statuses_accepted(self):
        """Every live DB enum value must be a valid ApplicationStatus."""
        import typing
        valid = set(typing.get_args(ApplicationStatus))
        assert valid == self._LIVE_DB_VALUES, (
            f"models.ApplicationStatus does not match live DB enum.\n"
            f"  Expected: {self._LIVE_DB_VALUES}\n"
            f"  Got:      {valid}"
        )

    def test_removed_values_not_present(self):
        import typing
        valid = set(typing.get_args(ApplicationStatus))
        for bad in self._REMOVED_VALUES:
            assert bad not in valid, (
                f"'{bad}' must NOT be in ApplicationStatus — it is not a valid DB enum value"
            )
