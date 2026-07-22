from pydantic import BaseModel, EmailStr


class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True  # lets this schema read directly from a SQLAlchemy model


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
