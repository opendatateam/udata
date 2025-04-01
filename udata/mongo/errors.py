from mongoengine.errors import ValidationError


class FieldValidationError(ValidationError):
    field: str

    def __init__(self, message: str, *args, field: str, **kwargs):
        super().__init__(*args, **kwargs)

        self.field = field
        self.errors[self.field] = message
