"""
Tests for filename utility functions.
"""

import pytest
from datetime import datetime
from core.utils.filename_utils import create_hybrid_filename

def test_create_hybrid_filename():
    """Test the hybrid filename creation function."""
    # Test with normal text
    result = create_hybrid_filename("A1B2C3D4", "Project Update Meeting", ".eml")
    assert result.startswith(datetime.now().strftime('%Y-%m-%d'))
    assert "_Project_Updat_A1B2C3D4.eml" in result
    
    # Test with special characters
    result = create_hybrid_filename("E5F6G7H8", "Report: Q1 2024!", ".pdf")
    assert result.startswith(datetime.now().strftime('%Y-%m-%d'))
    assert "_Report_Q1_2024_E5F6G7H8.pdf" in result
    
    # Test with very long text
    result = create_hybrid_filename("I9J0K1L2", "This is a very long subject that should be truncated", ".docx")
    assert result.startswith(datetime.now().strftime('%Y-%m-%d'))
    assert "_This_is_a_very_I9J0K1L2.docx" in result
    
    # Test with no text
    result = create_hybrid_filename("M3N4O5P6", "", ".txt")
    assert result.startswith(datetime.now().strftime('%Y-%m-%d'))
    assert f"_{datetime.now().strftime('%Y-%m-%d')}_M3N4O5P6.txt" in result 