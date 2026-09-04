from typing import Optional
from pydantic import BaseModel, Field

class AuthBody(BaseModel):
    username: str
    password: str
    confirmar_senha: Optional[str] = None
    dispositivo_cliente: Optional[dict] = None
