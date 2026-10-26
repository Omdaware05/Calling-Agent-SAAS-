import pytest
from app.services.call_service import (
    STATUS_BUSY,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STATUS_INITIATING,
    STATUS_NO_ANSWER,
    STATUS_RINGING,
    normalize_dograh_status,
    validate_and_normalize_phone,
)


def test_valid_phone_numbers():
    # US format
    assert validate_and_normalize_phone("+14155552671") == "+14155552671"
    # India format
    assert validate_and_normalize_phone("+919876543210") == "+919876543210"
    # Without plus if country code present
    assert validate_and_normalize_phone("919876543210") == "+919876543210"
    # With spaces/hyphens
    assert validate_and_normalize_phone("+1 (415) 555-2671") == "+14155552671"


def test_invalid_phone_numbers():
    with pytest.raises(ValueError):
        validate_and_normalize_phone("")

    with pytest.raises(ValueError):
        validate_and_normalize_phone("123")

    with pytest.raises(ValueError):
        validate_and_normalize_phone("not-a-number")


def test_status_normalization():
    assert normalize_dograh_status("initiated") == STATUS_INITIATING
    assert normalize_dograh_status("ringing") == STATUS_RINGING
    assert normalize_dograh_status("in-progress") == STATUS_IN_PROGRESS
    assert normalize_dograh_status("answered") == STATUS_IN_PROGRESS
    assert normalize_dograh_status("completed") == STATUS_COMPLETED
    assert normalize_dograh_status("busy") == STATUS_BUSY
    assert normalize_dograh_status("no-answer") == STATUS_NO_ANSWER
    assert normalize_dograh_status("failed") == STATUS_FAILED
    assert normalize_dograh_status(None) == STATUS_INITIATING
