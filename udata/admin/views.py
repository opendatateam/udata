from flask import render_template
from udata.auth import login_required
from udata.i18n import I18nBlueprint


blueprint = I18nBlueprint('admin', __name__, url_prefix='/admin')


@blueprint.route('/', defaults={'path': ''})
@blueprint.route('/<path:path>')
@login_required
def index(path):
    return render_template('admin.html')
