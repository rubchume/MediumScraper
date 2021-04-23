from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class ErrorCodes(Enum):
    OK = 0
    MISSING_SCHEMA = 1
    CONNECTION_ERROR = 2
    NOT_FOUND = 3
    DECODING_ERROR = 4


@dataclass
class Article:
    id: str
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    paragraphs: Optional[List[str]] = None
    error_code: ErrorCodes = ErrorCodes.OK
