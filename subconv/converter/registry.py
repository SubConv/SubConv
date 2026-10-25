"""Name registry for proxy name deduplication."""

from __future__ import annotations


class NameRegistry:
    """Tracks proxy names per subscription to ensure uniqueness.

    When a duplicate name is encountered, appends a zero-padded suffix
    (e.g., "HK-01", "HK-02").
    """

    def __init__(self) -> None:
        self._names: dict[str, int] = {}
        self._used: set[str] = set()

    def register(self, name: str) -> str:
        """Register a proxy name and return a unique version.

        First occurrence returns the name unchanged.
        Subsequent occurrences return "{name}-{index:02d}".
        """
        candidate = name
        index = self._names.get(name, 0)
        while candidate in self._used:
            index += 1
            candidate = f"{name}-{index:02d}"
        self._names[name] = index
        self._used.add(candidate)
        return candidate
