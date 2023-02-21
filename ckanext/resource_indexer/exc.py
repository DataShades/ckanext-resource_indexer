from __future__ import annotations

import magic


class ResourceIndexerError(Exception):
    pass


class FileError(ResourceIndexerError):
    def __init__(self, filepath: str):
        self.filepath = filepath

    def __str__(self):
        return f"File {self.filepath} cannot be processed"


class UnexpectedEncodingError(FileError):
    def __init__(self, filepath: str, e: UnicodeDecodeError):
        super().__init__(filepath)

        start = max(0, e.start - 10)
        end = e.end + 10

        self.original = e
        self.problem = e.object[e.start:e.end]
        self.context = e.object[start:end]

    def __str__(self):
        return (
            f"File {self.filepath} has an unexpected character at position {self.original.start}: {self.problem}"
            f" Context: {self.context}"
        )

class UnexpectedContentError(FileError):
    def __init__(self, filepath: str):
        super().__init__(filepath)

        with open(filepath, "rb") as source:
            self.chunk = source.read(1024)
            self.mimetype = magic.from_buffer(self.chunk, True)

    def __str__(self):
        return (
            f"File {self.filepath} has an unexpected type or content."
            f" Mimetype: {self.mimetype}. First 100 bytes of content:"
            f" {self.chunk[:100]}"
        )
