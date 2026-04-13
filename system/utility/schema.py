"""
Defines and validates the input schema for the /agent endpoint
and the output schema for the agent's response
"""

from pydantic import BaseModel, Field, field_validator, model_validator
# from fastapi.exceptions import RequestValidationError


class UserInputSchema(BaseModel):
    """Enforces input requirements for the /agent endpoint"""
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=6,
        description="Stock ticker symbol (alphabetical characters only)"
    )

    # standardize tickers
    @field_validator('ticker', mode='before')
    def normalize_ticker(self):
        """Standardize ticker to uppercase"""
        if not isinstance(self.ticker, str):
            raise ValueError('Ticker must be in letters')
        self.ticker = self.ticker.upper()
        return self

    # enforce only alphabetic inputs
    @model_validator(mode='after')
    def validate_alphabetical(self):
        """Ensure ticker contains only alphabetical characters"""
        if not self.ticker.isalpha():
            raise ValueError(
                'Ticker must contain only alphabetical characters'
                )
        return self

class AgentOutputSchema(BaseModel):
    """Schema for agent response"""
    final_summary: str = Field(..., description="Summary of stock analysis")
    status: str = Field(default="success", description="Response status")
    timestamp: str = Field(..., description="Timestamp of analysis")
