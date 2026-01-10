"""Exceptions for pygocoax client library."""


class GoCoaxError(Exception):
    """Base exception for goCoax errors."""


class GoCoaxConnectionError(GoCoaxError):
    """Connection error to goCoax adapter."""


class GoCoaxAuthError(GoCoaxError):
    """Authentication error with goCoax adapter."""


class GoCoaxTimeoutError(GoCoaxError):
    """Timeout error communicating with goCoax adapter."""


class GoCoaxParseError(GoCoaxError):
    """Error parsing response from goCoax adapter."""
