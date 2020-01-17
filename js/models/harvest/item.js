import {Model} from 'models/base';
import log from 'logger';
import {_} from 'i18n';


export const STATUS_CLASSES = {
    'pending': 'default',
    'started': 'info',
    'done': 'success',
    'failed': 'danger',
    'skipped': 'warning',
    'archived': 'warning'
};

export const STATUS_I18N = {
    'pending': _('Pending'),
    'started': _('Started'),
    'done': _('Done'),
    'failed': _('Failed'),
    'skipped': _('Skipped'),
    'archived': _('Archived')
};

export default class HarvestItem extends Model {};
