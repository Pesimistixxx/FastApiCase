from pydantic import BaseModel, Field


class BattleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=40)
    players_cnt: int = Field(ge=2, le=4)
    case_id: int
    case_cnt: int = Field(ge=1, le=10)
