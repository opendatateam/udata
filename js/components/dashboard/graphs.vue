<style lang="less">
.box {
    border: none;
}
</style>
<template>
    <div class="row">
        <chart class="col-xs-12" title="{{ _('Data') }}"
            metrics="{{ metrics }}" icon="null"
            y="{{ dataY }}"></chart>
    </div>
    <div class="row" v-if="communityY">
        <chart class="col-xs-12" title="{{ _('Community') }}"
            metrics="{{ metrics }}" icon="null"
            y="{{ communityY }}"></chart>
    </div>
</template>

<script>
import Metrics from 'models/metrics';
import moment from 'moment';
import site from 'models/site';

export default {
    el: "#graphs",
    name: 'GraphView',
    props: ['objectId'],
    data: function() {
        var dataY, communityY;
        if (this.objectId) {
            dataY = [{
                id: 'datasets',
                label: this._('Datasets')
            }, {
                id: 'dataset_views',
                label: this._('Views')
            }, {
                id: 'resource_downloads',
                label: this._('Downloads')
            }];
        } else {
            dataY = [{
                id: 'datasets',
                label: this._('Datasets')
            }, {
                id: 'reuses',
                label: this._('Reuses')
            }, {
                id: 'resources',
                label: this._('Resources')
            }];
            communityY = [{
                id: 'users',
                label: this._('Users')
            }, {
                id: 'organizations',
                label: this._('Organizations')
            }];
        }
        return {
            site: site,
            metrics: new Metrics({
                data: {
                    loading: true,
                }
            }),
            dataY: dataY,
            communityY: communityY
        };
    },
    components: {
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
                    start: moment().subtract(30, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                });
            }
        }
    }};
</script>
