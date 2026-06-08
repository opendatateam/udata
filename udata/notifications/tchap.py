from urllib.parse import quote

import requests
from flask import current_app
from markdown import markdown

from udata.core.spam.signals import on_new_potential_spam
from udata.tasks import task


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

    # The notification hits an external service (Tchap) and is only a side-effect
    # of the spam detection. Send it from a worker so a slow, unreachable or
    # misconfigured Tchap never delays nor breaks the user request that triggered
    # the detection (e.g. publishing a dataset).
    send_message.delay(message)


@task(route="low.tchap")
def send_message(text: str):
    """Send a message to the Tchap moderation room.

    Args:
        text (str): Text to send to the room
    """
    homeserver = current_app.config.get("TCHAP_HOMESERVER")
    room_id = current_app.config.get("TCHAP_ROOM_ID")
    token = current_app.config.get("TCHAP_BOT_TOKEN")
    if not (homeserver and room_id and token):
        return

    # The room id is URL-encoded as it contains reserved chars (e.g. `!` and `:`).
    url = (
        f"{homeserver.rstrip('/')}/_matrix/client/v3/rooms/"
        f"{quote(room_id, safe='')}/send/m.room.message"
    )

    r = requests.post(
        url,
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
        },
        json={
            "msgtype": "m.text",
            "body": text,
            "format": "org.matrix.custom.html",
            "formatted_body": markdown(text),
            "m.mentions": {"room": True},
        },
    )
    r.raise_for_status()
