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

    /**
     * Create or update the given dataset.
     */
    save(on_error) {
        var ep = this.id ? 'datasets.update_dataset' : 'datasets.create_dataset';
        this.loading = true;
        this.$api(ep, {payload: this}, this.on_fetched, on_error);
    }

    update(data, on_success, on_error) {
        this.loading = true;
        this.$api('datasets.update_dataset', {
            dataset: this.id,
            payload: data
        }, on_success, on_error);
    }

    delete_resource(id) {
        this.$api('datasets.delete_resource', {
            dataset: this.id,
            rid: id
        }, () => {
            this.fetch(this.id);
        });
    }

    save_resource(resource) {
        var endpoint = resource.id ? 'datasets.update_resource' : 'datasets.create_resource',
            payload = resource.hasOwnProperty('$data') ? resource.$data : resource;

        this.$api(endpoint, {
            dataset: this.id,
            rid: resource.id,
            payload: payload
        }, () => {
            this.fetch(this.id);
        });
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
