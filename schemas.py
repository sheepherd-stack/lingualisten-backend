from pydantic import BaseModel, Field
from typing import List, Optional

class MaterialCreate(BaseModel):
    title: str
    transcript: str

class MaterialOut(BaseModel):
    id: int
    title: str
    audio_path: Optional[str] = None
    transcript: str
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str
    material_id: int
    modes: List[str] = Field(default_factory=lambda: ["shadowing","dictation","retell","summary"]) 
    difficulty: str = "A2"

class TaskOut(BaseModel):
    id: int
    title: str
    material_id: int
    modes: List[str]
    difficulty: str
    class Config:
        from_attributes = True

class SplitRequest(BaseModel):
    min_len: int = 2
    max_len: int = 300

class DictationSubmit(BaseModel):
    user_id: str
    task_id: int
    sentence_id: int
    expected: str
    text: str

class ShadowingSubmit(BaseModel):
    user_id: str
    task_id: int
    sentence_id: int
    duration_ms: int
    reference_ms: int

class RetellSubmit(BaseModel):
    user_id: str
    task_id: int
    sentence_id: int
    reference: str
    text: str

class SummarySubmit(BaseModel):
    user_id: str
    task_id: int
    reference: str
    text: str