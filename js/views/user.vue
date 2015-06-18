<template>
    <div class="row">
        <user-profile user="{{user}}" class="col-md-6"></user-profile>
        <chart title="Traffic" metrics="{{metrics}}" class="col-md-6"
            x="date" y="{{y}}"></chart>
    </div>

    <div class="row">
        <datasets-widget class="col-xs-12" datasets="{{datasets}}"></datasets-widget>
    </div>

    <div class="row">
        <reuses-widget class="col-xs-12" reuses="{{reuses}}"></reuses-widget>
    </div>
</template>

<script>
'use strict';

var moment = require('moment'),
    User = require('models/user'),
    Reuses = require('models/reuses'),
    Datasets = require('models/datasets'),
    Metrics = require('models/metrics');

module.exports = {
    name: 'user-view',
    data: function() {
        return {
            user_id: null,
            user: new User(),
            metrics: new Metrics({
                query: {
                    start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                }
            }),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}}),
            datasets: new Datasets({query: {sort: '-created', page_size: 10}}),
            meta: {
                title: null,
                subtitle: this._('User')
            },
            y: [{
                id: 'datasets',
                label: this._('Datasets'),
                color: '#a0d0e0'
            }, {
                id: 'reuses',
                label: this._('Reuses'),
                color: '#3c8dbc'
            }]
        };
    },
    components: {
        'user-profile': require('components/user/profile.vue'),
        'chart': require('components/charts/widget.vue'),
        'datasets-widget': require('components/dataset/list.vue'),
        'reuses-widget': require('components/reuse/list.vue')
    },
    watch: {
        user_id: function(id) {
            if (id) {
                this.user.fetch(id);
            }
        },
        'user.id': function(id) {
            if (id) {
                this.metrics.fetch({id: id});
                this.reuses.clear().fetch({owner: id});
                this.datasets.clear().fetch({owner: id});
            } else {
                this.datasets.clear();
                this.reuses.clear();
            }
        },
        'user.fullname': function(fullname) {
            if (fullname) {
                this.meta.title = fullname;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    }
};
</script>
