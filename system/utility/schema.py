from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi.exceptions import RequestValidationError

class UserInputSchema(BaseModel):
    """enforces input requirements for the /agent endpoint"""
    ticker: str = Field(..., min_length= 3, max_length= 6)

    # Standardizing inputted tickers
    @model_validator(mode='before')
    def normalize_ticker(cls, values):
        # Ensure ticker is uppercase before other validations
        if "ticker" in values and isinstance(values["ticker"], str):
            values["ticker"] = values["ticker"].upper()
        return values

    # preventing entry of wrong data type into ticker field
    @model_validator(mode='after')  # tells to run post-default validations
    def validate_after(self):
        """validate user input after default validation"""
        if not isinstance(self.ticker, str) or not self.ticker.isalpha():
            raise RequestValidationError(
                'inputted tickers must be alphabetical only'
            )
        return self

class AgentOutputSchema(BaseModel):
    """schema for agent output"""
    final_summary: str
