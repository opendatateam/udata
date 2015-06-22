<template>
    <div class="row">
        <small-box class="col-lg-4 col-xs-6" v-repeat="boxes"></small-box>
    </div>
    <div class="row">
        <reuse-details reuse="{{reuse}}" class="col-md-6"></reuse-details>
        <datasets-list datasets="{{reuse.datasets}}" class="col-md-6"></datasets-list>
    </div>

    <div class="row">
        <chart title="Traffic" metrics="{{metrics}}" class="col-md-12"
            x="date" y="{{y}}"></chart>
    </div>

    <div class="row">
        <followers-widget id="followers-widget" class="col-xs-12" followers="{{followers}}"></followers-widget>
    </div>
</template>

<script>
'use strict';

var Vue = require('vue'),
    moment = require('moment'),
    Reuse = require('models/reuse'),
    Followers = require('models/followers').extend({ns: 'reuses'}),
    Metrics = require('models/metrics');

module.exports = {
    name: 'DatasetView',
    data: function() {
        return {
            reuse_id: null,
            reuse: new Reuse(),
            metrics: new Metrics({query: {
                start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                end: moment().format('YYYY-MM-DD')
            }}),
            followers: new Followers({query: {page_size: 10}}),
            meta: {
                title: null,
                page: null,
                subtitle: this._('Reuse'),
                actions: [{
                    label: this._('Transfer'),
                    icon: 'send',
                    method: 'transfer_request'
                },{
                    label: this._('Delete'),
                    icon: 'trash',
                    method: 'confirm_delete'
                }]
            },
            y: [{
                id: 'views',
                label: this._('Views')
            }, {
                id: 'followers',
                label: this._('Followers')
            }]
        };
    },
    computed: {
        boxes: function() {
            if (!this.reuse.metrics) {
                return [];
            }
            return [{
                value: this.reuse.metrics.reuses || 0,
                label: this.reuse.metrics.reuses ? this._('Reuses') : this._('Reuse'),
                icon: 'retweet',
                color: 'green'
            }, {
                value: this.reuse.metrics.followers || 0,
                label: this.reuse.metrics.followers ? this._('Followers') : this._('Follower'),
                icon: 'users',
                color: 'yellow',
                target: '#followers-widget'
            }, {
                value: this.reuse.metrics.views || 0,
                label: this._('Views'),
                icon: 'eye',
                color: 'purple'
            }];
        }
    },
    components: {
        'small-box': require('components/containers/small-box.vue'),
        'reuse-details': require('components/reuse/details.vue'),
        'chart': require('components/charts/widget.vue'),
        'datasets-list': require('components/dataset/card-list.vue'),
        'followers-widget': require('components/follow/list.vue')
    },
    events: {
        'dataset-card-list:submit': function(ids) {
            this.reuse.datasets = ids;
            this.reuse.save();
        }
    },
    methods: {
        confirm_delete: function() {
            var m = this.$root.$modal(
                {data: {dataset: this.dataset}},
                Vue.extend(require('components/dataset/delete-modal.vue'))
            );
        },
        transfer_request: function() {
            this.$root.$modal({
                    components: {
                        'transfer-card': require('components/reuse/card.vue')
                    },
                    data: {
                        cardparams: {
                            reuse: this.reuse
                        },
                        subject: this.reuse
                    }
                },
                Vue.extend(require('components/transfer/request-modal.vue'))
            );
        }
    },
    watch: {
        reuse_id: function(id) {
            if (id) {
                this.reuse.fetch(id);
            }
        },
        'reuse.title': function(title) {
            if (title) {
                this.meta.title = title;
                this.$dispatch('meta:updated', this.meta);
            }
        },
        'reuse.page': function(page) {
            if (page) {
                this.meta.page = page;
                this.$dispatch('meta:updated', this.meta);
            }
        },
        'reuse.id': function(id) {
            if (id) {
                this.metrics.fetch({id: id});
                this.followers.fetch({id: id});
            }
        }
    }
};
</script>
