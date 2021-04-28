from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Article:
    id: str
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    paragraphs: Optional[List[str]] = None
    duration_minutes: Optional[int] = None

    @property
    def num_words(self) -> int:
        if not self.paragraphs:
            return 0

        return sum([len(paragraph.split(" ")) for paragraph in self.paragraphs])
