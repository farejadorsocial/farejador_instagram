from typing import Optional
from pydantic import BaseModel, Field

class AnalyzeBody(BaseModel):
    username: str = Field(min_length=1)

class SaveProfileBody(BaseModel):
    dados: Optional[dict] = None

class MonitorBody(BaseModel):
    monitorando: bool
