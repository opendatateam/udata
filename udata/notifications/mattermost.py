import requests
from udata.tasks import connect
from udata.core.spam.signals import on_new_potential_spam
from flask import current_app

@connect(on_new_potential_spam)
def notify_potential_spam(title, link, text, reason):
    message = ':warning: @all Spam potentiel sur \n'
    if link:
        message += f'[{title}]({link})'
    else:
        message += title

    message += f' ({reason})\n\n'
    message += f'> {text}'

    send_message(message)


def send_message(text: str):
    """Send a message to a mattermost channel

    Args:
        text (str): Text to send to a channel
    """
    data = {'text': text}

    r = requests.post(current_app.config.get('MATTERMOST_WEBHOOK', []), json=data)
    r.raise_for_status()