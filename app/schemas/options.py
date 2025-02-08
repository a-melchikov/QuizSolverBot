from pydantic import BaseModel, ConfigDict


class OptionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    question_id: int
    option_text: str
    is_correct: bool = False


class OptionCreate(BaseModel):
    question_id: int
    option_text: str
    is_correct: bool = False
