from pydantic import BaseModel, Field, field_validator


def _check_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(v.encode()) > 72:
        raise ValueError("Password is too long (bcrypt limit is 72 bytes)")
    return v


class RegisterCompany(BaseModel):
    company_name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    password: str

    _pw = field_validator("password")(_check_password)


class Login(BaseModel):
    company_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class CreateUser(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str
    role: str

    _pw = field_validator("password")(_check_password)
