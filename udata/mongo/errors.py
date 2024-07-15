from mongoengine.errors import ValidationError


class FieldValidationError(ValidationError):
    field: str

    def __init__(self, *args, field: str, **kwargs):
        self.field = field
        super().__init__(*args, **kwargs)
