"""
Utility functions for handling filenames.
"""

from datetime import datetime
import os

def create_hybrid_filename(identifier: str, text: str, ext: str) -> str:
    """
    Create a hybrid filename with date, shortened text, and ID.
    
    Args:
        identifier: message_id or attachment_id
        text: subject or filename
        ext: file extension (without dot)
    
    Returns:
        Formatted filename like: 2024-03-20_Project_Update_Text{id}.ext
    """
    # Get current date
    date_prefix = datetime.now().strftime('%Y-%m-%d')
    
    # Clean and truncate text to exactly 20 chars
    clean_text = ''.join(c for c in text if c.isalnum() or c in (' ', '_'))
    clean_text = clean_text.replace(' ', '_')[:20]
    
    # Get first 8 chars of identifier
    short_id = identifier[:8]
    
    # Create filename with proper extension handling
    if not ext.startswith('.'):
        ext = f'.{ext}'
    
    return f"{date_prefix}_{clean_text}{short_id}{ext}" 