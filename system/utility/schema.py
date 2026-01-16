from pydantic import BaseModel


class UserInputSchema(BaseModel):
    ticker: str


class AgentOutputSchema(BaseModel):
    final_summary: str
