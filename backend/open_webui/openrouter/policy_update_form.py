from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
class PolicyUpdateForm(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope: Literal['global', 'model', 'group', 'user']
    target: str = Field(min_length=1, max_length=256)
    expected_version: int = Field(ge=0)
    rules: dict[str, dict] = Field(max_length=256)
