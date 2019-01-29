import {Model} from 'models/base';
import {_} from 'i18n';
import log from 'logger';

export const VALIDATION_STATUS_CLASSES = {
    'pending': 'default',
    'accepted': 'success',
    'refused': 'danger',
};

export const VALIDATION_STATUS_I18N = {
    'pending': _('Pending'),
    'accepted': _('Accepted'),
    'refused': _('Refused'),
};


export class HarvestSource extends Model {
    fetch(ident) {
        ident = ident || this.id || this.slug;
        this.loading = true;
        if (ident) {
            this.$api('harvest.get_harvest_source',
                {ident: ident},
                this.on_fetched
            );
        } else {
            log.error('Unable to fetch HarvestSource: no identifier specified');
        }
        return this;
    }

    /**
     * Create or update the given harvest source.
     */
    save(on_error) {
        if (this.id) {
            return this.update(this, on_error);
        }
        this.loading = true;
        this.$api('harvest.create_harvest_source', {payload: this}, this.on_fetched);
    }

    update(data, on_error) {
        this.loading = true;
        this.$api('harvest.update_harvest_source', {
            ident: this.id,
            payload: data
        }, this.on_fetched, on_error);
    }
}

export default HarvestSource;
