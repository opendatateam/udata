from mongoengine.errors import ValidationError


class FieldValidationError(ValidationError):
    field: str
    raw_message: str

    def __init__(self, message: str, *args, field: str, **kwargs):
        super().__init__(*args, **kwargs)

        self.raw_message = message  # It's sad but ValidationError do some stuff with the message…
        self.field = field
        self.errors[self.field] = message

    def __str__(self):
        return str(self.raw_message)
