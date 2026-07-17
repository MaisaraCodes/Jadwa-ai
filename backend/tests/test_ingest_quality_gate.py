"""
DB/LLM-free unit tests for the extraction quality gate in
data/ingest_oracle_corpus.py.

Tests confirm:
  - Normal logical-order Arabic passes the gate.
  - Empty / short text quarantines as "image-only".
  - Presentation-form-heavy strings quarantine as "likely garbled".
  - Exactly at the 15% threshold does NOT quarantine (strictly greater than).
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

# data/ is not on sys.path by default
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "data"))

from ingest_oracle_corpus import (
    MIN_EXTRACT_CHARS,
    PRES_FORM_THRESHOLD,
    ExtractionStats,
    extraction_stats,
    quality_gate,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# 300+ chars of clean logical-order Arabic (no presentation forms).
# Repeated to comfortably exceed MIN_EXTRACT_CHARS.
_CLEAN_ARABIC = (
    "يُعدّ قطاع المنشآت الصغيرة والمتوسطة ركيزةً أساسية في الاقتصاد السعودي، "
    "إذ يُسهم بنسبة تتجاوز ثلاثين بالمئة من الناتج المحلي الإجمالي. "
    "وتُولي رؤية المملكة اهتمامًا بالغًا بتمكين هذا القطاع وتطويره. "
) * 5


def _presform_heavy(block_count: int = 800, pres_count: int = 200) -> str:
    """Build a string where pres_count/(block_count+pres_count) > 15%."""
    # U+0643 ARABIC LETTER KAF — standard block char
    # U+FE80 ARABIC LETTER HAMZA ISOLATED FORM — presentation form (FB50–FDFF)
    return ("\u0643" * block_count + "\uFE80" * pres_count) * 3


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCleanArabicPasses:
    def test_passes_quality_gate(self):
        stats = extraction_stats(_CLEAN_ARABIC)
        reason = quality_gate(_CLEAN_ARABIC, stats)
        assert reason is None, f"Expected PASS but quarantined: {reason!r}"

    def test_presform_pct_is_zero(self):
        stats = extraction_stats(_CLEAN_ARABIC)
        assert stats.presform_pct == 0.0

    def test_char_count_above_minimum(self):
        stats = extraction_stats(_CLEAN_ARABIC)
        assert stats.char_count >= MIN_EXTRACT_CHARS


class TestEmptyQuarantines:
    def test_empty_string(self):
        text = ""
        stats = extraction_stats(text)
        reason = quality_gate(text, stats)
        assert reason is not None
        assert "image-only" in reason
        assert "0 chars" in reason

    def test_whitespace_only(self):
        text = "   \n\t  "
        stats = extraction_stats(text)
        reason = quality_gate(text, stats)
        assert reason is not None
        assert "image-only" in reason


class TestShortTextQuarantines:
    def test_single_word(self):
        text = "مرحبا"
        stats = extraction_stats(text)
        reason = quality_gate(text, stats)
        assert reason is not None
        assert "image-only" in reason

    def test_just_below_minimum(self):
        # MIN_EXTRACT_CHARS - 1 chars of Arabic text
        text = "\u0643" * (MIN_EXTRACT_CHARS - 1)
        stats = extraction_stats(text)
        reason = quality_gate(text, stats)
        assert reason is not None
        assert "image-only" in reason


class TestPresformHeavyQuarantines:
    def test_20_percent_presforms_quarantines(self):
        """200 / (800 + 200) = 20% > 15% threshold → must quarantine."""
        text = _presform_heavy(block_count=800, pres_count=200)
        stats = extraction_stats(text)
        reason = quality_gate(text, stats)
        assert reason is not None, (
            f"Expected quarantine (presform_pct={stats.presform_pct:.1%}) but passed"
        )
        assert "pres-forms" in reason

    def test_presform_pct_computed_correctly(self):
        text = _presform_heavy(block_count=800, pres_count=200)
        stats = extraction_stats(text)
        # 200 / 1000 = 0.20
        assert abs(stats.presform_pct - 0.20) < 1e-9


class TestThresholdBoundary:
    def test_exactly_at_threshold_passes(self):
        """presform_pct == 15.0% exactly should NOT quarantine (strictly >)."""
        # 150 pres-forms, 850 block → 150/1000 = 15.0%
        text = ("\u0643" * 850 + "\uFE80" * 150) * 3
        stats = extraction_stats(text)
        assert abs(stats.presform_pct - 0.15) < 1e-9
        # Only quarantine on presform if char_count >= MIN_EXTRACT_CHARS
        if stats.char_count >= MIN_EXTRACT_CHARS:
            reason = quality_gate(text, stats)
            assert reason is None, (
                f"Exactly at threshold should pass but got: {reason!r}"
            )

    def test_one_over_threshold_quarantines(self):
        """151/1000 = 15.1% > 15% → must quarantine."""
        text = ("\u0643" * 849 + "\uFE80" * 151) * 3
        stats = extraction_stats(text)
        if stats.char_count >= MIN_EXTRACT_CHARS:
            reason = quality_gate(text, stats)
            assert reason is not None
            assert "pres-forms" in reason


class TestNKFCNormalizationEffect:
    def test_nfkc_converts_presforms_to_block(self):
        """NFKC maps many Arabic presentation forms back to block codepoints.
        After normalization, presform_pct should drop relative to raw input."""
        # U+FE80 is ARABIC LETTER HAMZA ISOLATED — NFKC maps it to U+0621
        raw_pres = "\uFE80" * 300
        normalized = unicodedata.normalize("NFKC", raw_pres)
        raw_stats = extraction_stats(raw_pres)
        norm_stats = extraction_stats(normalized)
        assert norm_stats.presform_pct < raw_stats.presform_pct, (
            "NFKC should reduce presentation-form percentage"
        )
