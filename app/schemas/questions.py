from pydantic import BaseModel, ConfigDict


class QuestionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    text: str
    has_options: bool
    answer_text: str | None = None
    created_by: int | None = None


class QuestionCreate(BaseModel):
    text: str
    has_options: bool = False
    answer_text: str | None = None
    created_by: int | None = None
