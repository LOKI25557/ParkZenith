from pydantic import EmailStr, ValidationError


def validate_email(email: str) -> bool:
    try:
        EmailStr.validate(email)
        return True
    except ValidationError:
        return False
