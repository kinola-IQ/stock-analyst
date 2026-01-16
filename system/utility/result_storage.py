"""module to store outputs from agents/tools

This is a lightweight default implementation which
provides a simple in-memory result storage.
"""
from typing import Dict, List, Optional

# third party modules
from ..utility.logger import logger


class ResultStorage:
    """Class to handle in-memory storage of results (stores instances)."""

    # store instances of ResultStorage
    memory: List["ResultStorage"] = []

    def __init__(self, content: Dict[str, str]) -> None:
        self.content: Dict[str, str] = content
        self.research_findings: Optional[str] = None
        self.final_report: Optional[str] = None
        # assign attributes based on provided content
        self.instantiated: bool = self._instantiated()
        # append the instance to class memory
        ResultStorage.memory.append(self)

    @classmethod
    def save(cls, content: Dict[str, str]) -> None:
        """Save a new result to memory (creates an instance)."""
        try:
            cls(content)
            logger.info("saved successfully")
        except Exception as err:
            logger.error(f"error, could not save: error message - {err}")

    def _instantiated(self) -> bool:
        """Assigns attributes from self.content and returns True on success."""
        try:
            # Expect content to be a dict with optional keys
            if not isinstance(self.content, dict):
                raise TypeError("content must be a dict")

            # Use .get to avoid KeyError and allow None values
            rf = self.content.get("research_findings")
            fr = self.content.get("final_report")

            if rf is not None:
                self.research_findings = rf
            if fr is not None:
                self.final_report = fr

            logger.info("attributes assigned")
            return True
        except Exception as err:
            logger.error(f"attributes could not be assigned: {err}")
            return False

    # Convenience helpers

    @classmethod
    def all(cls) -> List["ResultStorage"]:
        """Return all stored ResultStorage instances."""
        return list(cls.memory)

    @classmethod
    def clear(cls) -> None:
        """Clear in-memory storage."""
        cls.memory.clear()
        logger.info("memory cleared")

    @classmethod
    def find_by_key(cls, key: str, value: str) -> List["ResultStorage"]:
        """Return instances whose content has key==value."""
        return [inst for inst in cls.memory if inst.content.get(key) == value]
