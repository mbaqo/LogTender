from enum import Enum as PyEnum

class UserRole(str, PyEnum):
    ADMIN = "admin"
    PROVIDER = "provider"
    EMPLOYEE = "employee"

class Genders(str, PyEnum):
    MALE = "Male"
    FEMALE = "Female"
    NA = "N/A"

class Actions(str, PyEnum):
    CHECK_IN = "in"
    CHECK_OUT = "out"
    ABSENT = "absent"

class EntryTypes(str, PyEnum):
    GUARDIAN = "guardian_pin"
    PROVIDER= "provider_pin"

class ResetVerificationMethods(str, PyEnum):
    SMS_OTP = "sms_otp"
    EMAIL_OTP = "email_otp"

class ResetStatuses(str, PyEnum):
    PENDING = "pending"
    VERIFIED = "verified"

class AttendanceStatus(str, PyEnum):
    CAN_CHECK_IN = "can_check_in"
    CAN_CHECK_OUT = "can_check_out"
    IS_ABSENT = "is_absent"