<template>
    <div class="row">
        <small-box class="col-lg-3 col-xs-6" v-repeat="boxes"></small-box>
    </div>

    <div class="row">
        <chart title="{{ _('Data')}}" metrics="{{metrics}}" class="col-md-12"
            x="date" y="{{y}}"></chart>
    </div>
</template>

<script>
'use strict';

var moment = require('moment'),
    Metrics = require('models/metrics');

module.exports = {
    name: 'Home',
    data: function() {
        return {
            metrics: new Metrics({
                data: {
                    loading: true,
                },
                query: {
                    start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                }
            }),
            y: [{
                id: 'datasets',
                label: this._('Datasets'),
                color: '#a0d0e0'
            }, {
                id: 'reuses',
                label: this._('Reuses'),
                color: '#3c8dbc'
            }, {
                id: 'users',
                label: this._('Users'),
                color: '#4da74d'
            }, {
                id: 'organizations',
                label: this._('Organizations'),
                color: '#ffb311'
            }]
            // charts: {
            //     data: {
            //         title: this._('Data'),
            //         y: [{
            //             id: 'datasets',
            //             label: this._('Datasets'),
            //             color: '#3c8dbc'
            //         }, {
            //             id: 'reuses',
            //             label: this._('Reuses'),
            //             color: '#a0d0e0'
            //         }]
            //     },
            //     community: {
            //         title: this._('Community'),
            //         y: [{
            //             id: 'users',
            //             label: this._('Users'),
            //             color: '#3c8dbc'
            //         }, {
            //             id: 'organizations',
            //             label: this._('Organizations'),
            //             color: '#a0d0e0'
            //         }]
            //     },
            //     all: {
            //         title: this._('Metrics'),
            //         series: {
            //             datasets: this._('Datasets'),
            //             reuses: this._('Reuses'),
            //             users: this._('Users'),
            //             organizations: this._('Organizations'),
            //         }
            //     }
            // }
        };
    },
    computed: {
        meta: function() {
            return {
                title: this._('Dashboard')
            };
        },
        boxes: function() {
            if (!this.$root.site.metrics) {
                return [];
            }
            return [{
                value: this.$root.site.metrics.datasets || 0,
                label: this._('Datasets'),
                icon: 'cubes',
                color: 'aqua',
                target: '#datasets-widget'
            }, {
                value: this.$root.site.metrics.reuses || 0,
                label: this._('Reuses'),
                icon: 'retweet',
                color: 'green',
                target: '#reuses-widget'
            }, {
                value: this.$root.site.metrics.users || 0,
                label: this._('Users'),
                icon: 'users',
                color: 'yellow',
                target: '#users-widget'
            }, {
                value: this.$root.site.metrics.organizations || 0,
                label: this._('Organizations'),
                icon: 'building',
                color: 'purple',
                target: '#organizations-widget'
            }];
        }
    },
    components: {
        'chart': require('components/charts/widget.vue'),
        'small-box': require('components/containers/small-box.vue'),
        'w-cal': require('components/calendar.vue')
    },
    watch: {
        '$root.site.id': function(id) {
            this.fetch_metrics();
        }
    },
    attached: function() {
        this.fetch_metrics();
    },
    methods: {
        fetch_metrics: function() {
            if (this.$root.site.id) {
                this.metrics.fetch({
                    id: this.$root.site.id,
                    // start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    // end: moment().format('YYYY-MM-DD')
                });
            }
        }
    }
};
</script>
