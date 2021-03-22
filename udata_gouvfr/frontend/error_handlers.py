import logging

from udata.auth import PermissionDenied
from udata_gouvfr import theme
from udata_gouvfr.frontend import front

log = logging.getLogger(__name__)


@front.app_errorhandler(ValueError)
def validation_error(error):
    error_label = '{0.__class__.__name__}({0})'.format(error)
    log.error('Uncaught error: %s', error_label, exc_info=True)
    return theme.render('errors/400.html', error=error), 400


@front.app_errorhandler(403)
@front.app_errorhandler(PermissionDenied)
def forbidden(error):
    return theme.render('errors/403.html', error=error), 403


@front.app_errorhandler(404)
def page_not_found(error):
    return theme.render('errors/404.html', error=error), 404


@front.app_errorhandler(410)
def page_deleted(error):
    return theme.render('errors/410.html', error=error), 410


@front.app_errorhandler(500)
def internal_error(error):
    return theme.render('errors/500.html', error=error), 500
