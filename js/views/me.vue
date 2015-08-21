<template>
    <div class="row">
        <user-profile user="{{$root.me}}" class="col-xs-12 col-md-6"></user-profile>
        <chart title="Traffic" metrics="{{metrics}}" class="col-xs-12 col-md-6"
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
import moment from 'moment';
import API from 'api';
import {PageList} from 'models/base';
import Metrics from 'models/metrics';

export default  {
    name: 'MeView',
    data: function() {
        return {
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
    computed: {
        meta: function() {
            return {
                title: this._('Me'),
                subtitle: this.$root.me.fullname
            }
        }
    },
    components: {
        'user-profile': require('components/user/profile.vue'),
        'chart': require('components/charts/widget.vue'),
        'datasets-widget': require('components/dataset/list.vue'),
        'reuses-widget': require('components/reuse/list.vue')
    },
    attached: function() {
        this.update();
        this.$root.me.$on('updated', this.update.bind(this));
    },
    methods: {
        update: function() {
            if (this.$root.me.id) {
                this.meta.title = this.$root.me.fullname;
                this.$dispatch('meta:updated', this.meta);
                this.metrics.fetch({
                    id: this.$root.me.id,
                    start: moment().subtract(15, 'days').format('YYYY-MM-DD'),
                    end: moment().format('YYYY-MM-DD')
                });
                var options = {
                    owner: this.$root.me.id,
                    sort: '-created',
                    page_size: 10
                };
                this.datasets.fetch();
                this.reuses.fetch();
                // this.reuses.clear().fetch(options);
                // this.datasets.clear().fetch(options);
            } else {
                // this.reuses.clear();
                // this.datasets.clear();
            }
        }
    }
};
</script>
