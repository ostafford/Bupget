"""
API error handling utilities.

This module provides shared error handling functionality for API integrations,
including exception classes, error responses, and retry mechanisms.
"""

import functools
import logging
import time
import random
from typing import Dict, Any, Optional, List, Type, Union, Callable
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout, HTTPError

# Configure logging
logger = logging.getLogger(__name__)


# Base exception classes
class APIError(Exception):
    """Base exception for API errors."""
    pass


class APIAuthError(APIError):
    """Exception for authentication errors."""
    pass


class APIResponseError(APIError):
    """Exception for API response errors."""
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class APIRateLimitError(APIResponseError):
    """Exception for rate limit errors."""
    def __init__(self, message, retry_after=None, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)


class APIConnectionError(APIError):
    """Exception for connection errors."""
    pass


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


def parse_error_response(response, error_type="API Error"):
    """
    Parse an error response from an API call.
    
    Args:
        response: The response object from requests
        error_type: Type of error for the message
        
    Returns:
        tuple: (error_message, error_details)
    """
    status_code = response.status_code
    error_message = f"{error_type}: {status_code}"
    error_details = {}
    
    # Try to get error details from response
    try:
        error_data = response.json()
        if 'errors' in error_data and error_data['errors']:
            error_detail = error_data['errors'][0].get('detail', 'Unknown error')
            error_message = f"{error_type} ({status_code}): {error_detail}"
            error_details = error_data
    except:
        # If we can't parse the JSON, use the status code and text
        error_message = f"{error_type} ({status_code}): {response.text}"
    
    return error_message, error_details


def handle_request_error(error, operation="API request"):
    """
    Create a standardized error response from a request error.
    
    Args:
        error: The exception that occurred
        operation: The operation that was being performed
        
    Returns:
        tuple: (error_message, should_retry, retry_after)
    """
    error_message = f"Error during {operation}: {str(error)}"
    should_retry = False
    retry_after = None
    
    if isinstance(error, ConnectionError):
        error_message = f"Connection error during {operation}: {str(error)}"
        should_retry = True
    elif isinstance(error, Timeout):
        error_message = f"Timeout during {operation}: {str(error)}"
        should_retry = True
    elif isinstance(error, HTTPError):
        error_message = f"HTTP error during {operation}: {str(error)}"
        should_retry = error.response.status_code >= 500 if hasattr(error, 'response') else False
    elif isinstance(error, RequestException):
        error_message = f"Request error during {operation}: {str(error)}"
        should_retry = True
    
    # Check for rate limiting
    if hasattr(error, 'response') and error.response.status_code == 429:
        retry_after = int(error.response.headers.get('Retry-After', 1))
        should_retry = True
    
    return error_message, should_retry, retry_after
