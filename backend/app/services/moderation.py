import re
from dataclasses import dataclass
from typing import Iterable, List, Optional


class ModerationError(ValueError):
    pass


DEFAULT_SENSITIVE_WORDS = [
    "未成年人色情",
    "儿童色情",
    "自杀教程",
    "制毒",
    "买卖枪支",
    "血腥虐杀",
]


@dataclass
class ModerationResult:
    passed: bool
    reason: str = ""
    matched: Optional[List[str]] = None


class TextModerator:
    def __init__(self, words: Optional[Iterable[str]] = None) -> None:
        self.words = [word.strip().lower() for word in (words or DEFAULT_SENSITIVE_WORDS) if word.strip()]

    def check(self, text: str) -> ModerationResult:
        normalized = re.sub(r"\s+", "", (text or "").lower())
        matched = [word for word in self.words if word and word in normalized]
        if matched:
            return ModerationResult(False, "内容包含敏感词，请调整描述后再试", matched)
        return ModerationResult(True)

    def ensure_safe(self, text: str) -> None:
        result = self.check(text)
        if not result.passed:
            raise ModerationError(result.reason)
