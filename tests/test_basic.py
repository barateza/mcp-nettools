"""Basic tests for mcp-nettools."""

import pytest
from mcp_nettools.server import is_valid_hostname, is_valid_ip, is_valid_target


def test_is_valid_hostname():
    """Test hostname validation function."""
    # RFC 952 compliant hostnames (should remain valid)
    assert is_valid_hostname("example.com") is True
    assert is_valid_hostname("sub.example.com") is True
    assert is_valid_hostname("example-site.com") is True
    
    # RFC 1035 compliant - service records with underscores
    assert is_valid_hostname("_dkim.example.com") is True
    assert is_valid_hostname("_dmarc.example.com") is True
    assert is_valid_hostname("_tcp.example.com") is True
    assert is_valid_hostname("default._domainkey.example.com") is True
    assert is_valid_hostname("_ldap._tcp.example.com") is True
    
    # Invalid names (should remain invalid)
    assert is_valid_hostname("192.168.1.1") is False
    assert is_valid_hostname("not_valid") is False  # Single label with underscore is still invalid
    assert is_valid_hostname("") is False
    assert is_valid_hostname("-invalid.com") is False
    assert is_valid_hostname("invalid-.com") is False


def test_is_valid_ip():
    """Test IP validation function."""
    assert is_valid_ip("192.168.1.1") is True
    assert is_valid_ip("8.8.8.8") is True
    assert is_valid_ip("2001:db8::1") is True  # IPv6
    assert is_valid_ip("example.com") is False
    assert is_valid_ip("256.256.256.256") is False
    assert is_valid_ip("") is False


def test_is_valid_target():
    """Test target validation function."""
    assert is_valid_target("example.com") is True
    assert is_valid_target("192.168.1.1") is True
    assert is_valid_target("192.168.1.0/24") is True  # CIDR notation
    assert is_valid_target("not_valid") is False
    assert is_valid_target("") is False