from pydantic import BaseModel

class APIError(BaseModel):
    code: str
    message: str
    details: dict | None = None

class ErrorResponse(BaseModel):
    error: APIError
