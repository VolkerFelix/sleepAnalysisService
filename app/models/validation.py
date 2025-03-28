from typing import Optional

from pydantic import BaseModel


class ValidationResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
