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