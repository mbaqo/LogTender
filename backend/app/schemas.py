import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing import Literal, Optional

from .enums import UserRole, Genders, Actions, EntryTypes, ResetVerificationMethods, ResetStatuses, AttendanceStatus

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    profile_picture: Optional[str] = Field(default=None)
    role: UserRole = Field(default = UserRole.PROVIDER)
    facility_name: str = Field(min_length=1, max_length=200)
    facility_address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    license_number: Optional[str] = Field(default=None, min_length=1, max_length=50)

class UserCreate(UserBase):
    password: str = Field(min_length=8)
    pin: str = Field(min_length=5, max_length=5)

class UserUpdateProfile(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    profile_picture: Optional[str] = Field(default=None)
    role: Optional[UserRole] = Field(default = None)
    facility_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    facility_address: Optional[str] = Field(default=None, min_length=1, max_length=255)
    license_number: Optional[str] = Field(default=None, min_length=1, max_length=50)

class UserUpdateEmail(BaseModel):
    email: EmailStr

class UserUpdatePassword(BaseModel):
    password: str = Field(min_length=8)

class UserUpdatePin(BaseModel):
    pin: str = Field(min_length=5, max_length=5)


# Students
class StudentBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=100)
    profile_picture: Optional[str] = Field(default=None)
    date_of_birth: datetime.date
    gender: Genders = Field(default=Genders.NA)
    medical_note: Optional[str] = Field(default=None, min_length=1, max_length=350)
    state_id: Optional[str] = Field(default=None, min_length=1, max_length=50)

class GuardianLinkCreate(BaseModel):
    guardian_public_id: uuid.UUID
    relationship_to_student: str = Field(min_length=1, max_length=50)

class StudentCreate(StudentBase):
    guardian_links: list[GuardianLinkCreate] = Field(default_factory=list)

class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=100)
    profile_picture: Optional[str] = Field(default=None)
    date_of_birth: Optional[datetime.date] = Field(default=None)
    gender: Optional[Genders] = Field(default=None)
    state_id: Optional[str] = Field(default=None, min_length=1, max_length=50)

class StudentUpdateMedicalNote(BaseModel):
    medical_note: Optional[str] = Field(default=None, min_length=1, max_length=350)


# Guardians
class GuardianBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone_number: PhoneNumber
    profile_picture: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    residential_address: Optional[str] = Field(default=None, min_length=1, max_length=255)

class StudentLinkCreate(BaseModel):
    student_public_id: uuid.UUID
    relationship_to_student: str = Field(min_length=1, max_length=50)

class GuardianCreate(GuardianBase):
    pin: str = Field(min_length=5, max_length=5)
    student_links: list[StudentLinkCreate] = Field(default_factory=list)

class GuardianUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    profile_picture: Optional[str] = Field(default=None)
    phone_number: Optional[PhoneNumber] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    residential_address: Optional[str] = Field(default=None, min_length=1, max_length=255)

class GuardianStudentLinksUpdate(BaseModel):
    add_student_public: list[uuid.UUID] = Field(default_factory=list)
    remove_student_public_ids: list[uuid.UUID] = Field(default_factory=list)

# Guardian Pin Actions
class GuardianPinResetRequest(BaseModel):
    guardian_public_id: uuid.UUID
    verification_method: ResetVerificationMethods

class GuardianPinResetVerify(BaseModel):
    reset_public_id: uuid.UUID
    code: str = Field(min_length=5, max_length=5)

class GuardianPinResetComplete(BaseModel):
    reset_public_id: uuid.UUID
    new_pin: str = Field(min_length=5, max_length=5)

class AttendanceLogBase(BaseModel):
    student_public_id: uuid.UUID
    # Event time should be the created_at (now)
    # for check-in/out
    guardian_signature_url: str = Field(max_length=512)
    authorized_person_name: str = Field(min_length=1, max_length=50)

class AttendanceCheckInCreate(AttendanceLogBase): 
    action: Literal[Actions.CHECK_IN] = Actions.CHECK_IN
    entry_type: Literal[EntryTypes.GUARDIAN] = EntryTypes.GUARDIAN

class AttendanceCheckOutCreate(AttendanceLogBase):
    action: Literal[Actions.CHECK_OUT] = Actions.CHECK_OUT
    entry_type: Literal[EntryTypes.GUARDIAN] = EntryTypes.GUARDIAN

class AttendanceMarkAbsentCreate(BaseModel):
    action: Literal[Actions.ABSENT] = Actions.ABSENT
    entry_type: Literal[EntryTypes.PROVIDER] = EntryTypes.PROVIDER
    student_public_id: uuid.UUID

class AttendanceManualEntryCreate(BaseModel):
    student_public_id: uuid.UUID
    event_time: datetime.datetime
    entry_type: Literal[EntryTypes.PROVIDER] = EntryTypes.PROVIDER
    action: Literal[Actions.CHECK_IN, Actions.CHECK_OUT]

class AttendanceCorrection(BaseModel):
    student_public_id: uuid.UUID
    event_time: datetime.datetime
    entry_type: Literal[EntryTypes.PROVIDER] = EntryTypes.PROVIDER
    action: Literal[Actions.CHECK_IN, Actions.CHECK_OUT]
    # Remember to mark as void
    original_log_public_id: uuid.UUID

class AttendanceLogNoteBase(BaseModel):
    attendance_date: datetime.date
    note: str = Field(min_length=1)

class AttendanceLogNoteCreate(AttendanceLogNoteBase):
    student_public_id: uuid.UUID

class AttendanceLogNoteUpdate(BaseModel):
    note: Optional[str] = Field(default=None, min_length=1)

# Responses
class StudentLite(BaseModel):
    public_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    nickname: Optional[str] = Field(default=None, min_length=1, max_length=100)
    profile_picture: Optional[str] = Field(default=None)
    model_config = ConfigDict(from_attributes=True)

class GuardianLite(BaseModel):
    public_id: uuid.UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone_number: PhoneNumber
    profile_picture: Optional[str] = Field(default=None)
    model_config = ConfigDict(from_attributes=True)

class AttendanceLogLite(BaseModel):
    public_id: uuid.UUID
    created_at: datetime.datetime
    event_time: Optional[datetime.datetime] = Field(default=None)
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
    # List for that day
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

class AttendanceLogResponse(BaseModel):
    # Event time should be the created_at (now)
    # for check-in/out
    event_time: Optional[datetime.datetime] = Field(default=None)
    action: Actions
    entry_type: EntryTypes
    is_void: bool
    guardian_signature_url: Optional[str] = Field(default=None, max_length=512)
    authorized_person_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    created_at: datetime.datetime
    public_id: uuid.UUID
    student: StudentLite
    model_config = ConfigDict(from_attributes=True)

class AttendanceDayStatusResponse(BaseModel):
    event_time: Optional[datetime.datetime] = Field(default=None)
    authorized_person_name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    current_status: AttendanceStatus

class AttendanceLogNoteResponse(BaseModel):
    public_id: uuid.UUID
    attendance_date: datetime.date
    note: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
