"""Tests for the config utility module.

This module contains tests for the configuration utility functions, specifically
testing the environment variable management functionality. The tests cover:
- Retrieving existing environment variables
- Handling missing variables with default values
- Handling missing variables without default values
"""
import os
import pytest
from core.utils.config import get_env_variable

def test_get_env_variable_with_existing_value():
    """Test getting an environment variable that exists.
    
    This test verifies that:
    1. The function correctly retrieves an existing environment variable
    2. The value is returned exactly as stored
    """
    # Set a test environment variable
    os.environ['TEST_VAR'] = 'test_value'
    assert get_env_variable('TEST_VAR') == 'test_value'

def test_get_env_variable_with_default():
    """Test getting an environment variable that doesn't exist with a default value.
    
    This test verifies that:
    1. When a variable doesn't exist, the default value is returned
    2. The function handles missing variables gracefully
    """
    # Ensure the variable doesn't exist
    if 'NONEXISTENT_VAR' in os.environ:
        del os.environ['NONEXISTENT_VAR']
    assert get_env_variable('NONEXISTENT_VAR', 'default') == 'default'

def test_get_env_variable_without_default():
    """Test getting an environment variable that doesn't exist without a default value.
    
    This test verifies that:
    1. When a variable doesn't exist and no default is provided, None is returned
    2. The function handles missing variables gracefully without defaults
    """
    # Ensure the variable doesn't exist
    if 'NONEXISTENT_VAR' in os.environ:
        del os.environ['NONEXISTENT_VAR']
    assert get_env_variable('NONEXISTENT_VAR') is None 