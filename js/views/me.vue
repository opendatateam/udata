<template>
<layout :title="_('Me')" :subtitle="$root.me.fullname" :actions="actions">
    <div class="row">
        <profile :user="$root.me" class="col-xs-12 col-md-6"></profile>
        <chart title="Traffic" :metrics="metrics" class="col-xs-12 col-md-6"
            x="date" :y="y"></chart>
    </div>

    <div class="row">
        <datasets class="col-xs-12" :datasets="datasets"></datasets>
    </div>

    <div class="row">
        <reuses class="col-xs-12" :reuses="reuses"></reuses>
    </div>
    <div class="row">
        <apikey class="col-xs-12 col-md-6" :user="$root.me"></apikey>
        <harvesters class="col-xs-12 col-md-6" :owner="$root.me"></harvesters>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import API from 'api';
import {PageList} from 'models/base';
import Metrics from 'models/metrics';
import Layout from 'components/layout.vue';

export default  {
    name: 'MeView',
    data: function() {
        return {
            actions: [{
                label: this._('Edit'),
                icon: 'edit',
                method: this.edit
            }],
            metrics: new Metrics(),
            reuses: new PageList({
                ns: 'me',
                fetch: 'my_reuses'
            }),
            datasets: new PageList({
                ns: 'me',
                fetch: 'my_datasets'
            }),
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
        profile: require('components/user/profile.vue'),
        chart: require('components/charts/widget.vue'),
        datasets: require('components/dataset/list.vue'),
        reuses: require('components/reuse/list.vue'),
        apikey: require('components/user/apikey.vue'),
        harvesters: require('components/harvest/sources.vue'),
        Layout
    },
    attached: function() {
        this.update();
        this._handler = this.$root.me.$on('updated', this.update.bind(this));
    },
    detached: function() {
        this._handler.remove();
    },
    methods: {
        edit() {
            this.$go({name: 'me-edit'});;
        },
        update: function() {
            if (this.$root.me.id) {
                this.metrics.fetch({
                    id: this.$root.me.id,
                    start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                });
                this.datasets.fetch();
                this.reuses.fetch();
            }
        }
    }
};
</script>
