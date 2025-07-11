from fastapi import Form
from pydantic import BaseModel, Field
from typing import List


class CaseCreate(BaseModel):
    name: str = Field(min_length=3, max_length=20)
    price: int = Field(ge=0, le=1000000)
    math_exception: int = Field(ge=1, le=1000000)
    sigma: int = Field(ge=1, le=1000000)
    skins: List[int]


class CaseCalculateProbability(BaseModel):
    math_exception: int = Field(ge=1, le=1000000)
    sigma: int = Field(ge=1, le=1000000)
    skins: List[int]


async def calculate_probability_form(
        math_exception: int = Form(),
        sigma: int = Form(),
        skins: List[int] = Form(),

) -> CaseCalculateProbability:
    return CaseCalculateProbability(
        math_exception=math_exception,
        sigma=sigma,
        skins=skins,
    )


class CaseOpen(BaseModel):
    cnt: int = Field(ge=1, le=10)