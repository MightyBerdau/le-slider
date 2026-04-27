"""
Unit tests for network utility functions.

Tests get_local_ip() and network functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
import socket
from functions.network import get_local_ip


def test_get_local_ip_returns_string():
    """Test that get_local_ip returns a string."""
    result = get_local_ip()
    assert isinstance(result, str)


def test_get_local_ip_valid_format():
    """Test that returned IP is in valid IPv4 format."""
    result = get_local_ip()
    parts = result.split('.')
    # Should have 4 parts
    assert len(parts) == 4
    # Each part should be a valid number 0-255
    for part in parts:
        num = int(part)
        assert 0 <= num <= 255


def test_get_local_ip_not_empty():
    """Test that get_local_ip doesn't return empty string."""
    result = get_local_ip()
    assert len(result) > 0
    assert result != ''


@patch('socket.socket')
def test_get_local_ip_uses_socket(mock_socket_class):
    """Test that get_local_ip uses socket module."""
    mock_socket = MagicMock()
    mock_socket.__enter__.return_value = mock_socket
    mock_socket.getsockname.return_value = ('192.168.1.100', 12345)
    mock_socket_class.return_value = mock_socket
    
    result = get_local_ip()
    
    # Should have called socket.socket with AF_INET and SOCK_DGRAM
    mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_DGRAM)
    # Should have called connect
    mock_socket.connect.assert_called_once()
    assert result == '192.168.1.100'
