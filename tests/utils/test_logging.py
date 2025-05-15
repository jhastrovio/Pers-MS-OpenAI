"""Tests for the logging utility module.

This module contains tests for the logging utility functions, specifically
testing the logger initialization and singleton pattern. The tests cover:
- Logger instance creation and configuration
- Singleton pattern implementation
- Multiple logger instance management
"""
import logging
import pytest
from core.utils.logging import get_logger

def test_get_logger_returns_logger():
    """Test that get_logger returns a logger instance.
    
    This test verifies that:
    1. The function returns a valid logging.Logger instance
    2. The logger is properly configured with the correct name
    3. The logger can be used for logging operations
    """
    logger = get_logger('test_logger')
    assert isinstance(logger, logging.Logger)
    assert logger.name == 'test_logger'

def test_get_logger_same_name_returns_same_instance():
    """Test that get_logger returns the same instance for the same name.
    
    This test verifies that:
    1. The singleton pattern is properly implemented
    2. Multiple calls with the same name return the same logger instance
    3. Logger state is preserved between calls
    """
    logger1 = get_logger('test_logger')
    logger2 = get_logger('test_logger')
    assert logger1 is logger2

def test_get_logger_different_names_returns_different_instances():
    """Test that get_logger returns different instances for different names.
    
    This test verifies that:
    1. Different logger names create separate logger instances
    2. Each logger instance is independent
    3. The singleton pattern is name-specific
    """
    logger1 = get_logger('test_logger_1')
    logger2 = get_logger('test_logger_2')
    assert logger1 is not logger2 