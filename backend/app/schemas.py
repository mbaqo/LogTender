import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional

from .enums import UserRole, Genders

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    profile_picture: Optional[str] = Field(default=None)
    role: UserRole = Field(default = UserRole.PROVIDER)
    facility_name: str = Field(min_length=1, max_length=50)
    facility_address: Optional[str] = Field(default=None, min_length=1, max_length=100)
    license_number: Optional[str] = Field(default=None, min_length=1, max_length=25)

class UserCreate(UserBase):
    password: str
    pin: str

class UserUpdateProfile(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    profile_picture: Optional[str] = Field(default=None)
    role: Optional[UserRole] = Field(default = None)
    facility_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    facility_address: Optional[str] = Field(default=None, min_length=1, max_length=100)
    license_number: Optional[str] = Field(default=None, min_length=1, max_length=25)

class UserUpdateEmail(BaseModel):
    email: EmailStr

class UserUpdatePassword(BaseModel):
    password: str

class UserUpdatePin(BaseModel):
    pin: str



# Students
class StudentBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=50)
    profile_picture: Optional[str] = Field(default=None)
    date_of_birth: datetime.date
    gender: Genders = Field(default=Genders.NA)
    medical_note: Optional[str] = Field(default=None, min_length=1, max_length=350)
    state_id: Optional[str] = Field(default=None, min_length=1, max_length=25)

class GuardianLinkCreate(BaseModel):
    guardian_public_id: uuid.UUID
    relationship_to_student: str = Field(min_length=1, max_length=50)

class StudentCreate(StudentBase):
    guardian_links: list[GuardianLinkCreate] = Field(default_factory=list)

class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=50)
    profile_picture: Optional[str] = Field(default=None)
    date_of_birth: Optional[datetime.date] = Field(default=None)
    gender: Optional[Genders] = Field(default=None)
    state_id: Optional[str] = Field(default=None, min_length=1, max_length=25)

class StudentUpdateMedicalNote(BaseModel):
    medical_note: Optional[str] = Field(default=None, min_length=1, max_length=350)


# Guardians
class GuardianBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone_number: Optional[str] = Field(default=None, min_length=1, max_length=20)
    profile_picture: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    residential_address: Optional[str] = Field(default=None, min_length=1, max_length=100)

class StudentLinkCreate(BaseModel):
    student_public_id: uuid.UUID
    relationship_to_student: str = Field(min_length=1, max_length=50)

class GuardianCreate(GuardianBase):
    pin: str
    student_links: list[StudentLinkCreate] = Field(default_factory=list)

class GuardianUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    phone_number: Optional[str] = Field(default=None, min_length=1, max_length=20)
    email: Optional[EmailStr] = Field(default=None)
    residential_address: Optional[str] = Field(default=None, min_length=1, max_length=100)

class GuardianStudentLinksUpdate(BaseModel):
    add_student_public: list[uuid.UUID] = Field(default_factory=list)
    remove_student_public_ids: list[uuid.UUID]


# Responses
class StudentLite(BaseModel):
    public_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=50)
    profile_picture: Optional[str] = Field(default=None)
    model_config = ConfigDict(from_attributes=True)

class GuardianLite(BaseModel):
    public_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    phone_number: Optional[str] = Field(default=None, min_length=1, max_length=20)
    profile_picture: Optional[str] = Field(default=None)
    model_config = ConfigDict(from_attributes=True)

class StudentGuardianLinkResponse(BaseModel):
    guardian: GuardianLite
    relationship_to_student: str
    model_config = ConfigDict(from_attributes=True)

class GuardianStudentLinkResponse(BaseModel):
    student: StudentLite
    relationship_to_student: str
    model_config = ConfigDict(from_attributes=True)

class StudentResponse(StudentBase):
    public_id: uuid.UUID
    guardian_links: list[StudentGuardianLinkResponse] = Field(default_factory=list)
    attendance_logs: list[AttendanceLogLite] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class GuardianResponse(GuardianBase):
    public_id: uuid.UUID
    student_links: list[GuardianStudentLinkResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class UserResponse(UserBase):
    public_id: uuid.UUID
    students: list[StudentLite] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)