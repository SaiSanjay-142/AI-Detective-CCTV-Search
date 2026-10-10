from pydantic import BaseModel, Field
from typing import Literal

UnknownGender = Literal["male", "female", "unknown"]
class Clothing(BaseModel): type: str = "unknown"; color: str = "unknown"
class AttributePayload(BaseModel):
    gender: UnknownGender = "unknown"; upper_clothing: Clothing = Field(default_factory=Clothing); lower_clothing: Clothing = Field(default_factory=Clothing); accessories: list[str] = Field(default_factory=list); objects_held: list[str] = Field(default_factory=list); headwear: str = "unknown"; eyewear: str = "unknown"
class RegisterIn(BaseModel): email: str; password: str = Field(min_length=8, max_length=72)
class LoginIn(RegisterIn): pass
class SearchIn(BaseModel): query: str = Field(min_length=1, max_length=500); video_id: int | None = None
