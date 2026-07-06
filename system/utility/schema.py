"""Schema definitions for API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserInputSchema(BaseModel):
    """Ticker input validation schema."""
    ticker: str = Field(..., min_length=1, max_length=6, description="Stock ticker symbol")

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, value: str) -> str:
        """Validate and normalize ticker to uppercase."""
        value = value.strip().upper()
        if not value.isalpha():
            raise ValueError('Ticker must contain only alphabetical characters')
        return value


class AgentOutputSchema(BaseModel):
    """Agent response schema."""
    result: str = Field(..., description="full breadth of analysis carried out")
    findings: Optional[str] = Field(default=None, description="findings of the entire reasearch operation")
    plot: Optional[str] = Field(default=None, description="plot of the stock price over time")
    status: str = Field(default="success", description="Response status")
    timestamp: str = Field(..., description="Timestamp of analysis")
