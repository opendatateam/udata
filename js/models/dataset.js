'use strict';

import Model from 'models/model';
import API from 'api';


class Dataset extends Model {
    constructor(options) {
        super('Dataset', options);
    }

    fetch(ident) {
        ident = ident || this.id || this.slug;
        if (ident) {
            this.$api('datasets.get_dataset', {dataset: ident}, this.on_fetched);
        } else {
            log.error('Unable to fetch Dataset: no identifier specified');
        }
        return this;
    }

    save() {
        var method = this.id ? API.datasets.update_dataset : API.datasets.create_dataset;
        method({payload: this.$data}, this.on_fetched.bind(this));
    }

    update(data) {
        this.$api('datasets.update_dataset', {
            dataset: this.id,
            payload: data
        }, this.on_fetched);
    }

    delete_resource(id) {
        API.datasets.delete_resource({dataset: this.id, rid: id}, function(response) {
            this.fetch();
        }.bind(this));
    }

    save_resource(resource) {
        var method = resource.id ? API.datasets.update_resource : API.datasets.create_resource,
            payload = resource.hasOwnProperty('$data') ? resource.$data : resource;
        method({
            dataset: this.id,
            rid: resource.id,
            payload: payload
        }, function(response) {
            this.fetch();
        }.bind(this));
    }

    reorder(new_order) {
        API.datasets.reorder_resources({
            dataset: this.id,
            payload: new_order
        }, function(response) {
            this.$set('resources', response.obj);
        }.bind(this));
    }
}


define(['api', 'models/base', 'logger'], function(API, Model, log) {
    'use strict';

    var Dataset = Model.extend({
        name: 'Dataset',
        methods: {
            fetch: function(ident) {
                ident = ident || this.id || this.slug;
                if (ident) {
                    API.datasets.get_dataset({dataset: ident}, this.on_fetched.bind(this));
                } else {
                    log.error('Unable to fetch Dataset: no identifier specified');
                }
                return this;
            },
            save: function() {
                var method = this.id ? API.datasets.update_dataset : API.datasets.create_dataset;
                method({payload: this.$data}, this.on_fetched.bind(this));
            },
            update: function(data) {
                API.datasets.update_dataset({
                    dataset: this.id,
                    payload: data
                }, this.on_fetched.bind(this));
            },
            delete_resource: function(id) {
                API.datasets.delete_resource({dataset: this.id, rid: id}, function(response) {
                    this.fetch();
                }.bind(this));
            },
            save_resource: function(resource) {
                var method = resource.id ? API.datasets.update_resource : API.datasets.create_resource,
                    payload = resource.hasOwnProperty('$data') ? resource.$data : resource;
                method({
                    dataset: this.id,
                    rid: resource.id,
                    payload: payload
                }, function(response) {
                    this.fetch();
                }.bind(this));
            },
            reorder: function(new_order) {
                API.datasets.reorder_resources({
                    dataset: this.id,
                    payload: new_order
                }, function(response) {
                    this.$set('resources', response.obj);
                }.bind(this));
            }
        }
    });

    return Dataset;
});
