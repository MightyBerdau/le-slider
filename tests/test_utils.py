"""
Unit tests for utility functions.

Tests get_current_time() and other helper functions.
"""

import pytest
from datetime import datetime
from functions.utils import get_current_time


def test_get_current_time_returns_string():
    """Test that get_current_time returns a string."""
    result = get_current_time()
    assert isinstance(result, str)


def test_get_current_time_iso_format():
    """Test that get_current_time returns ISO format."""
    result = get_current_time()
    # ISO format should contain 'T' separator
    assert 'T' in result
    # Should contain timezone info (+ or - or Z)
    assert any(c in result for c in ['+', '-', 'Z'])


def test_get_current_time_is_parseable():
    """Test that returned timestamp can be parsed back to datetime."""
    result = get_current_time()
    # Should be parseable with fromisoformat
    dt = datetime.fromisoformat(result)
    assert dt is not None
    assert dt.tzinfo is not None  # Should have timezone info


def test_get_current_time_increments():
    """Test that consecutive calls return different times."""
    import time
    time1 = get_current_time()
    time.sleep(0.01)  # Sleep 10ms
    time2 = get_current_time()
    assert time1 != time2
    assert time2 > time1


def test_get_current_time_consistency():
    """Test that time is reasonable (within last few seconds)."""
    result = get_current_time()
    dt = datetime.fromisoformat(result)
    now = datetime.now().astimezone()
    # Difference should be less than 1 second
    diff = abs((now - dt).total_seconds())
    assert diff < 1.0
