"""
Retry utilities (DEPRECATED).

This module is deprecated. Please use app.api.error_handling instead.
The functionality has been moved to maintain better organization of error handling code.

All functions and classes are re-exported from error_handling for backwards compatibility.
"""

import warnings

# Show deprecation warning
warnings.warn(
    "app.utils.retry is deprecated. Use app.api.error_handling instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import and re-export from the new module to maintain backwards compatibility
from app.api.error_handling import (
    retry, handle_api_exception, APIErrorResponse, parse_error_response, handle_request_error
)

# Legacy class names can be aliased here if needed
# This allows old code to continue working without changes