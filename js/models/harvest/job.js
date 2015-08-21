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
    'failed': 'danger'
};

export const STATUS_I18N = {
    'pending': _('Pending'),
    'initializing': _('Initializing'),
    'initialized': _('Initialized'),
    'processing': _('Processing'),
    'done': _('Done'),
    'done-errors': _('Done with errors'),
    'failed': _('Failed')
}

export class HarvestJob extends Model {
    fetch() {
        if (this.id || this.slug) {
            this.$api('harvest.get_job', {
                dataset: this.id || this.slug
            }, this.on_fetched);
        } else {
            log.error('Unable to fetch Dataset: no identifier specified');
        }
        return this;
    }
};

export default HarvestJob;
