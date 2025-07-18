from typing import List
from pydantic import BaseModel


class ContractRequest(BaseModel):
    skins: List[int]
