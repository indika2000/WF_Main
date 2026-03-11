"""Unit tests for barcode normalisation."""

import pytest

from app.services.normalisation import (
    NormalisationError,
    build_canonical_id,
    normalise,
    normalise_ean_13,
    normalise_qr,
    normalise_upc_a,
)


class TestUPCA:
    """UPC-A normalisation tests."""

    def test_valid_upc_a(self):
        assert normalise_upc_a("012345678905") == "012345678905"

    def test_valid_upc_a_leading_zero(self):
        assert normalise_upc_a("000000000000") == "000000000000"

    def test_strips_whitespace(self):
        assert normalise_upc_a("  012345678905  ") == "012345678905"

    def test_too_short(self):
        with pytest.raises(NormalisationError, match="exactly 12 digits"):
            normalise_upc_a("12345")

    def test_too_long(self):
        with pytest.raises(NormalisationError, match="exactly 12 digits"):
            normalise_upc_a("0123456789012")

    def test_non_digits(self):
        with pytest.raises(NormalisationError, match="exactly 12 digits"):
            normalise_upc_a("01234567890A")

    def test_empty(self):
        with pytest.raises(NormalisationError):
            normalise_upc_a("")


class TestEAN13:
    """EAN-13 normalisation tests."""

    def test_valid_ean13(self):
        assert normalise_ean_13("5012345678900") == "5012345678900"

    def test_valid_ean13_leading_zero(self):
        assert normalise_ean_13("0000000000000") == "0000000000000"

    def test_strips_whitespace(self):
        assert normalise_ean_13("  5012345678900  ") == "5012345678900"

    def test_12_digit_upc_a_auto_converted(self):
        """12-digit UPC-A values are auto-converted to EAN-13 by prepending '0'."""
        assert normalise_ean_13("012345678905") == "0012345678905"

    def test_too_short(self):
        with pytest.raises(NormalisationError, match="12-13 digits"):
            normalise_ean_13("50123456789")

    def test_too_long(self):
        with pytest.raises(NormalisationError, match="12-13 digits"):
            normalise_ean_13("50123456789001")

    def test_non_digits(self):
        with pytest.raises(NormalisationError, match="12-13 digits"):
            normalise_ean_13("501234567890X")


class TestQR:
    """QR code normalisation tests."""

    def test_valid_qr(self):
        assert normalise_qr("https://example.com/product/123") == "https://example.com/product/123"

    def test_strips_whitespace(self):
        assert normalise_qr("  hello world  ") == "hello world"

    def test_empty_after_strip(self):
        with pytest.raises(NormalisationError, match="cannot be empty"):
            normalise_qr("   ")

    def test_too_long(self):
        with pytest.raises(NormalisationError, match="too long"):
            normalise_qr("x" * 4097)

    def test_preserves_content(self):
        value = "Special chars: !@#$%^&*()"
        assert normalise_qr(value) == value


class TestNormalise:
    """Top-level normalise() function tests."""

    def test_routes_upc_a(self):
        assert normalise("UPC_A", "012345678905") == "012345678905"

    def test_routes_ean_13(self):
        assert normalise("EAN_13", "5012345678900") == "5012345678900"

    def test_routes_qr(self):
        assert normalise("QR", "hello") == "hello"

    def test_case_insensitive(self):
        assert normalise("ean_13", "5012345678900") == "5012345678900"

    def test_unsupported_type(self):
        with pytest.raises(NormalisationError, match="Unsupported code type"):
            normalise("CODE_128", "12345")


class TestCanonicalId:
    """Canonical ID building tests."""

    def test_builds_canonical_id(self):
        result = build_canonical_id("EAN_13", "5012345678900")
        assert result == "EAN_13|5012345678900|WILDERNESS_FRIENDS|v1"

    def test_different_code_types(self):
        ean = build_canonical_id("EAN_13", "5012345678900")
        upc = build_canonical_id("UPC_A", "012345678905")
        assert ean != upc

    def test_different_values(self):
        a = build_canonical_id("EAN_13", "5012345678900")
        b = build_canonical_id("EAN_13", "5012345678901")
        assert a != b

    def test_upc_a_and_ean_13_same_barcode_same_canonical(self):
        """A UPC-A barcode detected as EAN_13 should produce the same
        canonical_id as when detected as UPC_A, after normalisation.
        Both mobile code_types now map to EAN_13, so the normaliser
        must convert 12-digit UPC-A to 13-digit EAN-13."""
        upc_value = "012345678905"
        ean_value = "0012345678905"  # same barcode, EAN-13 format
        normalised_from_12 = normalise("EAN_13", upc_value)
        normalised_from_13 = normalise("EAN_13", ean_value)
        assert normalised_from_12 == normalised_from_13
        assert build_canonical_id("EAN_13", normalised_from_12) == build_canonical_id("EAN_13", normalised_from_13)
