from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Article:
    id: str
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    paragraphs: Optional[List[str]] = None
