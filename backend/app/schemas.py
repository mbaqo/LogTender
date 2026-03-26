import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing import Optional

from .enums import UserRole, Genders, Actions, EntryTypes, ResetVerificationMethods, ResetStatuses

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
    password: str = Field(min_length=8)
    pin: str = Field(min_length=5, max_length=5)

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
    password: str = Field(min_length=8)

class UserUpdatePin(BaseModel):
    pin: str = Field(min_length=5, max_length=5)


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
    phone_number: PhoneNumber
    profile_picture: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    residential_address: Optional[str] = Field(default=None, min_length=1, max_length=100)

class StudentLinkCreate(BaseModel):
    student_public_id: uuid.UUID
    relationship_to_student: str = Field(min_length=1, max_length=50)

class GuardianCreate(GuardianBase):
    pin: str = Field(min_length=5, max_length=5)
    student_links: list[StudentLinkCreate] = Field(default_factory=list)

class GuardianUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    phone_number: Optional[PhoneNumber] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    residential_address: Optional[str] = Field(default=None, min_length=1, max_length=100)

class GuardianStudentLinksUpdate(BaseModel):
    add_student_public: list[uuid.UUID] = Field(default_factory=list)
    remove_student_public_ids: list[uuid.UUID]

# Guardian Pin Actions
class GuardianPinResetRequest(BaseModel):
    guardian_public_id: uuid.UUID
    verification_method: ResetVerificationMethods

class GuardianPinResetVerify(BaseModel):
    reset_public_id: uuid.UUID
    code: str = Field(min_length=5, max_length=5)

class GuardianPinResetComplete(BaseModel):
    reset_public_id: uuid.UUID
    new_code: str = Field(min_length=5, max_length=5)

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
    phone_number: PhoneNumber
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

class GuardianPinResetResponse(BaseModel):
    public_id: uuid.UUID
    status: ResetStatuses
    verification_method: ResetVerificationMethods
    expires_at: datetime.datetime
    created_at: datetime.datetime
    verified_at: Optional[datetime.datetime] = None
    guardian: GuardianLite
    model_config = ConfigDict(from_attributes=True)