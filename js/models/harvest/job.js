import {Model} from 'models/base';
import log from 'logger';
import {_} from 'i18n';


export const STATUS_CLASSES = {
    'pending': 'default',
    'initializing': 'primary',
    'initialized': 'info',
    'processing': 'info',
    'done': 'success',
    'done-errors': 'warning',
    'failed': 'danger',
    'deleted': 'danger',
};

export const STATUS_I18N = {
    'pending': _('Pending'),
    'initializing': _('Initializing'),
    'initialized': _('Initialized'),
    'processing': _('Processing'),
    'done': _('Done'),
    'done-errors': _('Done with errors'),
    'failed': _('Failed'),
    'deleted': _('Deleted'),
};

export class HarvestJob extends Model {
    fetch() {
        if (this.id) {
            this.loading = true;
            this.$api('harvest.get_harvest_job', {ident: this.id}, this.on_fetched);
        } else {
            log.error('Unable to fetch Job');
        }
        return this;
    }
}

export default HarvestJob;
