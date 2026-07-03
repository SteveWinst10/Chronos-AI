from typing import Generic, Optional, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class StandardResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: Optional[T] = None
    error: Optional[str] = None
