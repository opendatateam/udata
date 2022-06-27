from flask import current_app


def get_topic(message_type: str) -> str:
    return f"{current_app.config['UDATA_INSTANCE_NAME']}.{message_type}"
