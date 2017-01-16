<style lang="less">
.graphs {
    .small-boxes {
        margin: 1em 0 0;
    }
    .graphs-chart .box-title {
        margin-top: 0;
    }
}
</style>
<template>
<div class="graphs">
    <div v-if="metrics.loading" class="text-center"><span class="fa fa-4x fa-cog fa-spin"></span></div>
    <div v-if="!metrics.loading" class="row small-boxes">
        <small-box class="col-lg-4 col-xs-6" v-for="b in dataBoxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </small-box>
    </div>
    <div class="row small-boxes">
        <small-box class="col-lg-4 col-xs-6" v-for="b in communityBoxes"
        :value="b.value" :label="b.label" :color="b.color"
        :icon="b.icon" :target="b.target">
    </small-box>
    </div>
    <div class="row graphs-chart">
        <chart class="col-xs-6" :title="_('Latest dataset uploads')"
        :metrics="metrics" icon="null"
        :y="dataDatasets" chart-type="Line"></chart>
        <chart class="col-xs-6" :title="_('Latest reuse uploads')"
        :metrics="metrics" icon="null"
        :y="dataReuses" chart-type="Line"></chart>
    </div>
</div>
</template>

<script>
import Metrics from 'models/metrics';
import moment from 'moment';
import site from 'models/site';

export default {
    name: 'GraphView',
    props: ['objectId'],
    data: function() {
        return {
            site: site,
            metrics: new Metrics({
                data: {
                    loading: true,
                }
            }),
            dataDatasets: [{
                id: 'datasets',
                label: this._('Datasets')
            }],
            dataReuses: [{
                id: 'reuses',
                label: this._('Reuses')
            }]
        };
    },
    computed: {
        dataBoxes: function() {
            if (!this.$root.site.metrics) {
                return [];
            }
            return [{
                value: this.$root.site.metrics.datasets || 0,
                label: this._('Datasets'),
                icon: 'cubes',
                color: 'aqua',
            }, {
                value: this.$root.site.metrics.resources || 0,
                label: this._('Resources'),
                icon: 'file-text-o',
                color: 'maroon',
            }, {
                value: this.$root.site.metrics.reuses || 0,
                label: this._('Reuses'),
                icon: 'retweet',
                color: 'green',
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
            }, {
                value: this.$root.site.metrics.organizations || 0,
                label: this._('Organizations'),
                icon: 'building',
                color: 'purple',
            }, {
                value: this.$root.site.metrics.discussions || 0,
                label: this._('Discussions'),
                icon: 'comments',
                color: 'teal',
            }];
        }
    },
    components: {
        'small-box': require('components/containers/small-box.vue'),
        'chart': require('components/charts/widget.vue')
    },
    watch: {
        'site.id': function(id) {
            this.fetchMetrics();
        }
    },
    attached: function() {
        this.fetchMetrics();
    },
    methods: {
        fetchMetrics: function() {
            if (this.objectId || this.site.id) {
                this.metrics.fetch({
                    id: this.objectId || this.site.id,
                    start: moment().subtract(12, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD'),
                    cumulative: false
                });
            }
        }
    }
};
</script>
