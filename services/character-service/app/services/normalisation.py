"""Barcode normalisation — validate and canonicalize barcode inputs."""

import re

from app.services.config_loader import get_config


class NormalisationError(Exception):
    """Raised when a barcode value fails validation."""

    pass


def normalise_upc_a(raw_value: str) -> str:
    """Normalise a UPC-A barcode (12 digits, leading zeros preserved)."""
    value = raw_value.strip()
    if not re.match(r"^\d{12}$", value):
        raise NormalisationError(
            f"UPC-A must be exactly 12 digits, got '{raw_value}'"
        )
    return value


def normalise_ean_13(raw_value: str) -> str:
    """Normalise an EAN-13 barcode (13 digits, leading zeros preserved).

    Also accepts 12-digit UPC-A values and converts them to EAN-13
    by prepending '0'. This ensures consistent canonical_id generation
    regardless of whether the scanner detected UPC-A or EAN-13.
    """
    value = raw_value.strip()
    if re.match(r"^\d{12}$", value):
        # UPC-A detected as EAN_13 — convert to EAN-13 format
        value = "0" + value
    if not re.match(r"^\d{13}$", value):
        raise NormalisationError(
            f"EAN-13 must be 12-13 digits, got '{raw_value}'"
        )
    return value


def normalise_qr(raw_value: str) -> str:
    """Normalise a QR code (strip leading/trailing whitespace, preserve content)."""
    value = raw_value.strip()
    if not value:
        raise NormalisationError("QR code value cannot be empty")
    if len(value) > 4096:
        raise NormalisationError("QR code value too long (max 4096 chars)")
    return value


_NORMALISERS = {
    "UPC_A": normalise_upc_a,
    "EAN_13": normalise_ean_13,
    "QR": normalise_qr,
}

SUPPORTED_CODE_TYPES = list(_NORMALISERS.keys())


def normalise(code_type: str, raw_value: str) -> str:
    """Normalise a barcode value based on its type. Returns the normalised value."""
    code_type = code_type.upper().strip()
    normaliser = _NORMALISERS.get(code_type)
    if normaliser is None:
        raise NormalisationError(
            f"Unsupported code type '{code_type}'. Supported: {SUPPORTED_CODE_TYPES}"
        )
    return normaliser(raw_value)


def build_canonical_id(code_type: str, normalised_value: str) -> str:
    """Build the canonical identity string used for hashing.

    Format: CODE_TYPE|NORMALISED_VALUE|NAMESPACE|VERSION
    """
    config = get_config()
    return f"{code_type}|{normalised_value}|{config.namespace}|{config.version}"
