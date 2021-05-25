import logging
from dataclasses import dataclass


LOGGER = logging.getLogger(__name__)


@dataclass
class OrderError(object):
    code: str
    message: str
    error: list

    @classmethod
    async def parse_from_api(cls, error):
        return cls(error.code, error.message, error.error)


@dataclass
class OrderWarning(object):
    code: str
    message: str

    @classmethod
    async def parse_from_api(cls, warning):
        return cls(warning.code, warning.message)
