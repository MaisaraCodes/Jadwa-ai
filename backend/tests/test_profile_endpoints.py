"""
DB/LLM-free unit tests for the profile router.

Tests cover:
- PatchProfileRequest model validation (cr_number not accepted)
- _row_to_profile mapping
- Partial PATCH only sends supplied fields
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from routers.profile import PatchProfileRequest, _row_to_profile


# ---------------------------------------------------------------------------
# PatchProfileRequest — model validation
# ---------------------------------------------------------------------------

class TestPatchProfileRequest:
    def test_all_fields_optional(self):
        req = PatchProfileRequest()
        assert req.company_name is None
        assert req.sector is None
        assert req.district is None
        assert req.established_year is None
        assert req.backstory is None

    def test_cr_number_not_a_field(self):
        """cr_number must NOT be accepted by the PATCH model — it's read-only."""
        req = PatchProfileRequest(company_name="Test Co")
        assert not hasattr(req, "cr_number")

    def test_partial_update(self):
        req = PatchProfileRequest(sector="logistics", district="Riyadh")
        assert req.sector == "logistics"
        assert req.district == "Riyadh"
        assert req.company_name is None

    def test_established_year_integer(self):
        req = PatchProfileRequest(established_year=2018)
        assert req.established_year == 2018

    def test_partial_payload_dict_only_has_set_fields(self):
        """Verify that the update dict built from a partial request excludes Nones."""
        req = PatchProfileRequest(company_name="Acme", sector="retail")
        updates = {
            k: v for k, v in {
                "company_name": req.company_name,
                "sector": req.sector,
                "district": req.district,
                "established_year": req.established_year,
                "backstory": req.backstory,
            }.items()
            if v is not None
        }
        assert updates == {"company_name": "Acme", "sector": "retail"}


# ---------------------------------------------------------------------------
# _row_to_profile mapping
# ---------------------------------------------------------------------------

class TestRowToProfile:
    _ROW = {
        "id": "prof-uuid-1",
        "company_name": "Al Noor Trading",
        "cr_number": "1010123456",
        "sector": "logistics",
        "district": "Jeddah",
        "user_id": "user-uuid-1",
        "established_year": 2015,
        "backstory": "Founded in 2015",
    }

    def test_maps_all_fields(self):
        profile = _row_to_profile(self._ROW)
        assert profile.id == "prof-uuid-1"
        assert profile.company_name == "Al Noor Trading"
        assert profile.cr_number == "1010123456"
        assert profile.sector == "logistics"
        assert profile.district == "Jeddah"
        assert profile.user_id == "user-uuid-1"
        assert profile.established_year == 2015

    def test_cr_number_preserved(self):
        """cr_number must survive the mapping unchanged — forensic node keys on it."""
        profile = _row_to_profile(self._ROW)
        assert profile.cr_number == "1010123456"

    def test_missing_optional_fields_default_to_none(self):
        minimal = {
            "id": "p1",
            "company_name": "Test",
            "cr_number": "9999",
            "sector": "retail",
            "district": "Dammam",
        }
        profile = _row_to_profile(minimal)
        assert profile.user_id is None
        assert profile.established_year is None
        assert profile.backstory is None
