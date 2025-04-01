"""
Retry utilities.

This module provides functions and decorators for implementing retry
logic when making external API calls or other operations that might fail
temporarily.
"""

import time
import random
import logging
import functools
from typing import Callable, List, Any, Optional, Type, Dict, Union

# Configure logging
logger = logging.getLogger(__name__)


def retry(
    exceptions: Union[Type[Exception], List[Type[Exception]]],
    tries: int = 4, 
    delay: float = 1, 
    backoff: float = 2,
    jitter: float = 0.1,
    logger_name: Optional[str] = None
) -> Callable:
    """
    Retry decorator with exponential backoff.
    
    Args:
        exceptions: The exception(s) to catch for retrying
        tries: Number of times to try before giving up
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier e.g. value of 2 will double the delay each retry
        jitter: Jitter factor to add randomness to delay
        logger_name: Logger name for logging retries, defaults to function's module
        
    Returns:
        The decorated function
    """
    # Handle single exception or list of exceptions
    exceptions_to_catch = exceptions
    if not isinstance(exceptions, list):
        exceptions_to_catch = [exceptions]
    
    def decorator(func: Callable) -> Callable:
        # Set logger to use
        nonlocal logger_name
        logger_to_use = logger
        
        if logger_name:
            logger_to_use = logging.getLogger(logger_name)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Initialize variables for retry loop
            mtries, mdelay = tries, delay
            func_name = func.__qualname__
            
            # Try until we succeed or run out of tries
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions_to_catch) as e:
                    # Add jitter to delay
                    jitter_amount = random.uniform(-jitter, jitter)
                    effective_delay = mdelay * (1 + jitter_amount)
                    
                    # Log the exception and retry attempt
                    logger_to_use.warning(
                        f"Exception in {func_name}: {str(e)}. "
                        f"Retrying in {effective_delay:.2f} seconds... "
                        f"({mtries-1} tries left)"
                    )
                    
                    # Sleep before retrying
                    time.sleep(effective_delay)
                    
                    # Update retry parameters
                    mtries -= 1
                    mdelay *= backoff
                    
            # Last attempt
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


class APIErrorResponse:
    """
    Standardized API error response class.
    
    This class provides a consistent way to represent API errors
    throughout the application.
    """
    
    def __init__(
        self, 
        success: bool = False, 
        message: str = "An error occurred", 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None
    ):
        """
        Initialize the error response.
        
        Args:
            success: Whether the operation was successful (always False for errors)
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
            details: Optional dictionary with additional error details
            retry_after: Optional seconds to wait before retrying
        """
        self.success = success
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.retry_after = retry_after
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error response to a dictionary.
        
        Returns:
            Dictionary representation of the error
        """
        result = {
            "success": self.success,
            "message": self.message
        }
        
        if self.error_code:
            result["error_code"] = self.error_code
            
        if self.details:
            result["details"] = self.details
            
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
            
        return result
        
    def __str__(self) -> str:
        """String representation of the error response."""
        if self.error_code:
            return f"Error {self.error_code}: {self.message}"
        return self.message


def handle_api_exception(
    exception: Exception,
    service_name: str,
    operation: str,
    additional_context: Optional[Dict[str, Any]] = None
) -> APIErrorResponse:
    """
    Create a standardized error response from an exception.
    
    Args:
        exception: The exception that occurred
        service_name: Name of the service (e.g., "Up Bank API")
        operation: The operation that was being performed
        additional_context: Optional additional context for the error
        
    Returns:
        Standardized APIErrorResponse object
    """
    # Log the exception with the service and operation
    logger.error(
        f"Error in {service_name} during {operation}: {str(exception)}",
        exc_info=True
    )
    
    # Determine if this is a retryable error
    retry_after = None
    error_code = None
    
    # Handle specific exception types
    if hasattr(exception, 'response') and getattr(exception, 'response', None) is not None:
        status_code = getattr(exception.response, 'status_code', None)
        if status_code:
            error_code = f"HTTP_{status_code}"
            
            # Rate limiting typically uses 429 Too Many Requests
            if status_code == 429 and 'Retry-After' in exception.response.headers:
                retry_after = int(exception.response.headers['Retry-After'])
    
    # Prepare error details
    details = {
        "service": service_name,
        "operation": operation,
        "exception_type": type(exception).__name__
    }
    
    # Add any additional context
    if additional_context:
        details.update(additional_context)
    
    # Create standardized error response
    return APIErrorResponse(
        success=False,
        message=f"Error in {service_name}: {str(exception)}",
        error_code=error_code,
        details=details,
        retry_after=retry_after
    )
