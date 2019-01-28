import {Model} from 'models/base';
import log from 'logger';


export default class Dataset extends Model {
    /**
     * Fetch a dataset given its identifier, either an ID or a slug.
     * @param  {String} ident The dataset identifier to fetch.
     * @return {Dataset}      The current object itself.
     */
    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.loading = true;
            this.$api('datasets.get_dataset', {dataset: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch Dataset: no identifier specified');
        }
        return this;
    }

    get full_title() {
        if (!this.acronym) return this.title;
        return `${this.title} (${this.acronym})`;
    }

    /**
     * Create or update the given dataset.
     */
    save(on_error) {
        if (this.id) {
            return this.update(this, on_error);
        }
        this.loading = true;
        this.$api('datasets.create_dataset', {payload: this}, this.on_fetched, on_error);
    }

    update(data, on_error) {
        this.loading = true;
        this.$api('datasets.update_dataset', {
            dataset: this.id,
            payload: data
        }, this.on_fetched, on_error);
    }

    delete_resource(id, on_success, on_error) {
        this.$api('datasets.delete_resource', {
            dataset: this.id,
            rid: id
        }, () => {
            this.fetch(this.id);
            on_success(this);
        }, on_error);
    }

    save_resource(resource, on_error) {
        const endpoint = resource.id ? 'datasets.update_resource' : 'datasets.create_resource';
        const payload = resource.hasOwnProperty('$data') ? resource.$data : resource;

        this.$api(endpoint, {
            dataset: this.id,
            rid: resource.id,
            payload: payload
        }, () => this.fetch(this.id), on_error);
    }

    reorder(new_order) {
        this.$api('datasets.update_resources', {
            dataset: this.id,
            payload: new_order
        }, (response) => {
            this.resources = response.obj;
        });
    }
}

Dataset.__badges_type__ = 'dataset';
