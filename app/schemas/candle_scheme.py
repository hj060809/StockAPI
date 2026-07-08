from pydantic import BaseModel

class PurgeResult(BaseModel):
    deleted: int
