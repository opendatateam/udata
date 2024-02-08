import requests
from udata.core.spam.signals import on_new_potential_spam
from flask import current_app


@on_new_potential_spam.connect
def notify_potential_spam(sender, **kwargs):
    title = kwargs.get('title', 'no title')
    link = kwargs.get('link')
    reason = kwargs.get('reason')
    text = kwargs.get('text')

    message = ':warning: @all Spam potentiel sur '
    if link:
        message += f'[{title}]({link})'
    else:
        message += title

    if reason:
        message += f' ({reason})'

    if text:
        message += f'\n\n> {text}'

    send_message(message)


def send_message(text: str):
    """Send a message to a mattermost channel

    Args:
        text (str): Text to send to a channel
    """
    webhook = current_app.config.get('MATTERMOST_WEBHOOK')
    if not webhook:
        return

    data = {'text': text}

    r = requests.post(webhook, json=data)
    r.raise_for_status()
