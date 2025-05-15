import re
from datetime import datetime
import os

def format_timestamp(dt):
    """Format a datetime object as a string (YYYY-MM-DD HH:MM:SS)."""
    if not isinstance(dt, datetime):
        raise ValueError("Input must be a datetime object.")
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def sanitize_filename(filename):
    """Sanitize a filename by replacing spaces and special characters with underscores."""
    if not isinstance(filename, str):
        return ""
    # Replace path separators and special characters with underscores
    sanitized = re.sub(r'[\\/:*?"<>|@#]', '_', filename)
    # Replace spaces with underscores and collapse multiple underscores
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized.strip('_')

def get_file_extension(filename):
    """Get the file extension from a filename."""
    if not isinstance(filename, str) or '.' not in filename or filename.endswith('.'):
        return ""
    return os.path.splitext(filename)[1][1:]  # Exclude the dot

def is_valid_email(email):
    """Validate an email address using a regex pattern."""
    if not isinstance(email, str):
        return False
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    return re.match(pattern, email) is not None

def format_error_message(error):
    """Format an error message for logging.

    Args:
        error: The error object or message.

    Returns:
        A formatted error message.
    """
    return f"Error: {str(error)}"

def validate_input(data, required_fields):
    """Validate input data against required fields.

    Args:
        data: The input data to validate.
        required_fields: A list of required field names.

    Returns:
        True if all required fields are present, False otherwise.
    """
    return all(field in data for field in required_fields)

# Example usage
# if validate_input(user_data, ['username', 'email']):
#     process_user(user_data)
# else:
#     logger.error(format_error_message("Missing required fields"))
