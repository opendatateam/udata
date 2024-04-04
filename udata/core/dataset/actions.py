import logging
from datetime import datetime

from flask import current_app, render_template

from udata import i18n
from udata.models import Discussion, Message

log = logging.getLogger(__name__)


def archive(dataset, comment=False):
    """Archive a dataset"""
    if dataset.archived:
        log.warning('Dataset %s already archived, bumping date', dataset)
    dataset.archived = datetime.utcnow()
    dataset.save()

    if comment:
        log.info('Posting comment for dataset %s...', dataset)
        lang = current_app.config['DEFAULT_LANGUAGE']
        title = current_app.config['ARCHIVE_COMMENT_TITLE']
        user_id = current_app.config['ARCHIVE_COMMENT_USER_ID']
        if user_id:
            with i18n.language(lang):
                msg = render_template('comments/dataset_archived.txt')
                message = Message(content=msg, posted_by=user_id)
                discussion = Discussion(
                    user=user_id, discussion=[message], subject=dataset,
                    title=str(title))
                discussion.save()
        else:
            log.warning('ARCHIVE_COMMENT_USER_ID not set, skipping comment')

    log.info('Archived dataset %s', dataset)
