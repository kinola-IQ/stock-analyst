from pydantic import BaseModel, model_validator
from fastapi.exceptions import RequestValidationError

class UserInputSchema(BaseModel):
    ticker: str

    # setting up default validation
    @model_validator(mode='after') # tells to run right after the default validations
    def validate_after(self):
        if not isinstance(self.ticker, str):
            raise RequestValidationError(
                'must be alphabets'
            )
        return self


class AgentOutputSchema(BaseModel):
    final_summary: str
