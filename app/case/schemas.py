from pydantic import BaseModel, Field
from typing import List


class CaseCreate(BaseModel):
    name: str = Field(min_length=3, max_length=20)
    price: int = Field(ge=0, le=1000000)
    math_exception: int = Field(ge=1, le=1000000)
    sigma: int = Field(ge=1, le=1000000)
    image: str
    skins: List[int]


class CaseOpen(BaseModel):
    cnt: int = Field(ge=1, le=10)