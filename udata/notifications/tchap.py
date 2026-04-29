from markdown import markdown
import requests
from flask import current_app

from udata.core.spam.signals import on_new_potential_spam


@on_new_potential_spam.connect
def notify_potential_spam(sender, **kwargs):
    message = kwargs.get("message")
    reason = kwargs.get("reason")
    text = kwargs.get("text")

    message = f"⚠️ @all {message}"

    if reason:
        message += f" ({reason})"

    if text:
        message += f"\n\n> {text}"

    send_message(message)


def send_message(text: str):
    """Send a message to the Tchap moderation room

    Args:
        text (str): Text to send to the room
    """
    url = current_app.config.get("TCHAP_ROOM_URL")
    token = current_app.config.get("TCHAP_BOT_TOKEN")
    if not (url and token):
        return

    r = requests.post(
        url,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
        },
        json={
            "msgtype": "m.text",
            "body": "_",
            "format": "org.matrix.custom.html",
            "formatted_body": markdown(text),
            "m.mentions": {"room": True},
        },
    )
    r.raise_for_status()
