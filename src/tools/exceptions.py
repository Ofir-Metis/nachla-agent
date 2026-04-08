"""Custom exception classes for calculation tools.

These help the agent distinguish between:
- Bad input data (don't retry, fix the data)
- Transient failures (retry may help)
"""


class CalculationInputError(ValueError):
    """Bad input data — retrying won't help. Fix the data first.

    Examples: negative area, missing required field, invalid enum value.
    """


class TransientError(RuntimeError):
    """Transient failure — safe to retry.

    Examples: config file temporarily locked, network timeout for lookup.
    """
