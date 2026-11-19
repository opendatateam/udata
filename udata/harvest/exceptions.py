class HarvestException(Exception):
    """Base class for all harvest exception"""


class HarvestSkipException(HarvestException):
    """Raised when an item is skipped"""


class HarvestValidationError(HarvestException):
    """Raised when an harvested item is invalid"""
