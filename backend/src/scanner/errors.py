from __future__ import annotations


class ParserError(Exception):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class UnsupportedArchiveError(ParserError):
    pass


class CorruptArchiveError(ParserError):
    pass
