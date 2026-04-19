"""module to store outputs from agents/tools

This is a lightweight default implementation which
provides a simple in-memory result storage with memory limits and thread safety.
"""
from typing import Dict, List, Optional, Any
from collections import OrderedDict
import threading
from datetime import datetime

# third party modules
from ..utility.logger import logger


class ResultStorage:
    """Class to handle in-memory storage of results (stores instances).
    
    Thread-safe storage with configurable memory limit and LRU eviction.
    """

    # store instances of ResultStorage (OrderedDict for LRU)
    memory: OrderedDict["str", "ResultStorage"] = OrderedDict()
    _lock = threading.RLock()
    _max_items = 1000  # configurable memory limit

    def __init__(self, content: Dict[str, Any]) -> None:
        if not isinstance(content, dict):
            raise TypeError("content must be a dict")
        
        self.content: Dict[str, Any] = content
        self.ticker: Optional[str] = None
        self.response: Optional[str] = None
        self.research_findings: Optional[str] = None
        self.final_report: Optional[str] = None
        self.timestamp: datetime = datetime.now()
        
        # assign attributes based on provided content
        self._extract_attributes()
        
        # append the instance to class memory (thread-safe)
        with ResultStorage._lock:
            # Generate unique key
            key = f"{self.ticker or 'unknown'}_{len(ResultStorage.memory)}"
            ResultStorage.memory[key] = self
            
            # Enforce memory limit with LRU eviction
            if len(ResultStorage.memory) > ResultStorage._max_items:
                ResultStorage.memory.popitem(last=False)

    @classmethod
    def save(cls, content: Dict[str, Any]) -> None:
        """Save a new result to memory (creates an instance)."""
        try:
            if not isinstance(content, dict):
                logger.error("Invalid content type: must be a dict", extra={"type": type(content).__name__})
                return
            cls(content)
            logger.debug("Result saved successfully", extra={"keys": list(content.keys())})
        except TypeError as err:
            logger.error("Save failed: invalid content structure", extra={"error": str(err)})
        except Exception as err:
            logger.error("Save failed with unexpected error", extra={"error": type(err).__name__})

    def _extract_attributes(self) -> None:
        """Extract attributes from self.content, supporting multiple schemas."""
        try:
            # Support new schema: ticker and response
            ticker = self.content.get("ticker")
            response = self.content.get("response")
            
            if ticker is not None:
                self.ticker = str(ticker).strip().upper()
            if response is not None:
                self.response = str(response)
            
            # Support legacy schema: research_findings and final_report
            rf = self.content.get("research_findings")
            fr = self.content.get("final_report")
            
            if rf is not None:
                self.research_findings = str(rf)
            if fr is not None:
                self.final_report = str(fr)
            
            logger.debug("Attributes extracted", extra={"has_ticker": self.ticker is not None, "has_response": self.response is not None})
        except Exception as err:
            logger.error("Failed to extract attributes", extra={"error": type(err).__name__})

    # Convenience helpers

    @classmethod
    def all(cls) -> List["ResultStorage"]:
        """Return all stored ResultStorage instances (thread-safe)."""
        with cls._lock:
            return list(cls.memory.values())

    @classmethod
    def clear(cls) -> None:
        """Clear in-memory storage (thread-safe)."""
        with cls._lock:
            cls.memory.clear()
        logger.debug("Memory cleared")

    @classmethod
    def find_by_key(cls, key: str, value: Optional[str]) -> List["ResultStorage"]:
        """Return instances whose content has key==value (thread-safe)."""
        with cls._lock:
            return [
                inst for inst in cls.memory.values()
                if inst.content.get(key) == value
            ]
    
    @classmethod
    def find_by_ticker(cls, ticker: str) -> List["ResultStorage"]:
        """Return instances for a specific ticker symbol."""
        ticker = ticker.strip().upper()
        return [inst for inst in cls.all() if inst.ticker == ticker]
    
    @classmethod
    def count(cls) -> int:
        """Return total number of stored items."""
        with cls._lock:
            return len(cls.memory)
    
    @classmethod
    def set_max_items(cls, max_items: int) -> None:
        """Configure the maximum number of items to store (LRU eviction)."""
        if max_items < 1:
            raise ValueError("max_items must be at least 1")
        cls._max_items = max_items
