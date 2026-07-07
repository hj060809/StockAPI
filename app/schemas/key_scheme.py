from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ApiKeyCreate(BaseModel):
    name: str
    expires_at: datetime | None = None

class ApiKeyIssued(BaseModel):
    """ return only once """
    id: int
    name: str
    key: str
    key_prefix: str
    created_at: datetime
    expires_at: datetime | None

class ApiKeyRead(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    model_config = ConfigDict(from_attributes=True)