"""Tests for the helper utilities module.

This module contains tests for various helper utility functions, including:
- Timestamp formatting
- Filename sanitization
- File extension extraction
- Email validation

Each function is tested for both valid and invalid inputs, including edge cases.
"""
import pytest
from datetime import datetime
from core.utils.helpers import (
    format_timestamp,
    sanitize_filename,
    get_file_extension,
    is_valid_email
)

def test_format_timestamp():
    """Test timestamp formatting functionality.
    
    This test verifies that:
    1. The function correctly formats current time
    2. The output format is consistent (YYYY-MM-DD HH:MM:SS)
    3. Specific timestamps are formatted correctly
    4. The output is always a string of the correct length
    """
    # Test with current time
    now = datetime.now()
    formatted = format_timestamp(now)
    assert isinstance(formatted, str)
    assert len(formatted) == 19  # YYYY-MM-DD HH:MM:SS format

    # Test with specific time
    test_time = datetime(2024, 1, 1, 12, 0, 0)
    formatted = format_timestamp(test_time)
    assert formatted == "2024-01-01 12:00:00"

def test_sanitize_filename():
    """Test filename sanitization functionality.
    
    This test verifies that:
    1. Spaces are replaced with underscores
    2. Path separators are replaced with underscores
    3. Special characters are handled appropriately
    4. Multiple spaces are collapsed
    5. Empty strings are handled correctly
    """
    # Test basic sanitization
    assert sanitize_filename("test file.txt") == "test_file.txt"
    assert sanitize_filename("test/file.txt") == "test_file.txt"
    assert sanitize_filename("test\\file.txt") == "test_file.txt"
    
    # Test with special characters
    assert sanitize_filename("test@file.txt") == "test_file.txt"
    assert sanitize_filename("test#file.txt") == "test_file.txt"
    
    # Test with multiple spaces
    assert sanitize_filename("test   file.txt") == "test_file.txt"
    
    # Test with empty string
    assert sanitize_filename("") == ""

def test_get_file_extension():
    """Test file extension extraction functionality.
    
    This test verifies that:
    1. Simple extensions are correctly extracted
    2. Multiple dots in filename are handled correctly
    3. Files without extensions return empty string
    4. Files with trailing dots return empty string
    5. Empty strings are handled correctly
    """
    assert get_file_extension("test.txt") == "txt"
    assert get_file_extension("test.doc.docx") == "docx"
    assert get_file_extension("test") == ""
    assert get_file_extension("test.") == ""
    assert get_file_extension("") == ""

def test_is_valid_email():
    """Test email validation functionality.
    
    This test verifies that:
    1. Standard email formats are accepted
    2. Emails with dots in local part are accepted
    3. Emails with plus signs are accepted
    4. Emails with subdomains are accepted
    5. Various invalid formats are rejected
    6. Edge cases are handled correctly
    """
    # Valid emails
    assert is_valid_email("test@example.com")
    assert is_valid_email("test.name@example.com")
    assert is_valid_email("test+name@example.com")
    assert is_valid_email("test@sub.example.com")
    
    # Invalid emails
    assert not is_valid_email("test@")
    assert not is_valid_email("test@example")
    assert not is_valid_email("@example.com")
    assert not is_valid_email("test@.com")
    assert not is_valid_email("")
    assert not is_valid_email("test") 