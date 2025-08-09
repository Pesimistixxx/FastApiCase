from pydantic import BaseModel, Field


class SendMessage(BaseModel):
    message: str = Field(max_length=2000)


class EditMessage(BaseModel):
    message: str = Field(max_length=2000)
