# Defines request and response schemas for admin authentication.

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    client_id: str | None = None
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client_id: str
    username: str


class AdminMeResponse(BaseModel):
    client_id: str
    username: str


class AdminCredentialsUpdateRequest(BaseModel):
    client_id: str
    current_password: str
    new_username: str = Field(min_length=3, max_length=100)
    new_password: str = Field(min_length=6, max_length=128)


class AdminCredentialsUpdateResponse(BaseModel):
    status: str
    client_id: str
    username: str
