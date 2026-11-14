from pydantic import BaseModel


# Data submitted by the student registration form.
class StudentRegister(BaseModel):
    username: str
    password: str
    roll_number: str | None = None
    department: str | None = None
    programme: str | None = None
    semester: int | None = None
