from flask import url_for, redirect
from udata.i18n import I18nBlueprint


blueprint = I18nBlueprint('site', __name__)


@blueprint.route('/')
def home():
    return redirect(url_for('admin.index'))
