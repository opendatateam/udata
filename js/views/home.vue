<template>
    <div class="row">
        <small-box class="col-lg-4 col-xs-6" v-repeat="dataBoxes"></small-box>
    </div>

    <div class="row">
        <chart title="{{ _('Data') }}" metrics="{{ metrics }}" class="col-xs-12"
            x="date" y="{{ dataY }}"></chart>
    </div>

    <div class="row">
        <small-box class="col-lg-4 col-xs-6" v-repeat="communityBoxes"></small-box>
    </div>

    <div class="row">
        <chart title="{{ _('Community') }}" metrics="{{ metrics }}" class="col-xs-12"
            x="date" y="{{ communityY }}" icon="users"></chart>
    </div>
</template>

<script>
import moment from 'moment';
import Metrics from 'models/metrics';

export default {
    name: 'Home',
    data: function() {
        return {
            metrics: new Metrics({
                data: {
                    loading: true,
                }
            }),
            dataY: [{
                id: 'datasets',
                label: this._('Datasets')
            }, {
                id: 'reuses',
                label: this._('Reuses')
            }, {
                id: 'resources',
                label: this._('Resources')
            }],
            communityY: [{
                id: 'users',
                label: this._('Users')
            }, {
                id: 'organizations',
                label: this._('Organizations')
            }]
        };
    },
    computed: {
        meta: function() {
            return {
                title: this._('Dashboard')
            };
        },
        dataBoxes: function() {
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
                value: this.$root.site.metrics.resources || 0,
                label: this._('Resources'),
                icon: 'file-text-o',
                color: 'red',
                target: '#resources-widget'
            }];
        },
        communityBoxes: function() {
            if (!this.$root.site.metrics) {
                return [];
            }
            return [{
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
        'small-box': require('components/containers/small-box.vue')
    },
    watch: {
        '$root.site.id': function(id) {
            this.fetchMetrics();
        }
    },
    attached: function() {
        this.fetchMetrics();
    },
    methods: {
        fetchMetrics: function() {
            if (this.$root.site.id) {
                this.metrics.fetch({
                    id: this.$root.site.id,
                    start: moment().subtract(20, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                });
            }
        }
    }
};
</script>
