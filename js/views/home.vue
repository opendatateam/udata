<template>
<layout :title="_('Dashboard')">
    <div class="row">
        <sbox class="col-lg-3 col-xs-6" v-for="b in dataBoxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </sbox>
    </div>

    <div class="row">
        <reuse-list class="col-xs-12" :reuses="reuses"
            :title="_('Reuses about your data (including your organizations)')">
        </reuse-list>
    </div>

    <div class="row">
        <issues id="issues-widget" class="col-xs-12" :issues="issues"
            :title="_('Issues about your data (including your organizations)')">
        </issues>
    </div>

    <div class="row">
        <discussions id="discussions-widget" class="col-xs-12" :discussions="discussions"
            :title="_('Discussions about your data (including your organizations)')">
        </discussions>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import {PageList} from 'models/base';
import MyMetrics from 'models/mymetrics';
import Layout from 'components/layout.vue';
import ReuseList from 'components/reuse/list.vue';

export default {
    name: 'Home',
    data() {
        return {
            metrics: new MyMetrics(),
            reuses: new PageList({
                ns: 'me',
                fetch: 'my_org_reuses',
                mask: ReuseList.MASK
            }),
            issues: new PageList({
                ns: 'me',
                fetch: 'my_org_issues',
            }),
            discussions: new PageList({
                ns: 'me',
                fetch: 'my_org_discussions'
            }),
        };
    },
    computed: {
        dataBoxes() {
            if (!this.metrics.id || !this.reuses) {
                return []
            }
            let userDatasetsCount = this.metrics.datasets_count || 0;
            let orgDatasetsCount = this.metrics.datasets_org_count || 0;
            let userFollowersCount = this.metrics.followers_count || 0;
            let orgFollowersCount = this.metrics.followers_org_count || 0;
            let orgReusesCount = this.reuses.items.length || 0;
            let isGoodAvailability = this.metrics.resources_availability >= 80;
            return [{
                value: `${orgDatasetsCount} (${userDatasetsCount})`,
                label: this._('Datasets (only yours)'),
                icon: 'cubes',
                color: 'aqua',
            }, {
                value: (this.metrics.resources_availability || 0) + ' %',
                label: this._('Availability of your datasets'),
                icon: isGoodAvailability ? 'thumbs-up' : 'thumbs-down',
                color: isGoodAvailability ? 'green' : 'red',
            }, {
                value: `${orgFollowersCount} (${userFollowersCount})`,
                label: this._('Followers (only yours)'),
                icon: 'heart',
                color: 'purple',
            }, {
                value: orgReusesCount,
                label: this._('Reuses'),
                icon: 'retweet',
                color: 'teal',
            }];
        }
    },
    components: {
        sbox: require('components/containers/small-box.vue'),
        issues: require('components/issues/list.vue'),
        discussions: require('components/discussions/list.vue'),
        ReuseList,
        Layout
    },
    attached() {
        this.update();
        this._handler = this.$root.me.$on('updated', this.update.bind(this));
    },
    detached() {
        this._handler.remove();
    },
    methods: {
        update() {
            if (this.$root.me.id) {
                this.metrics.fetch();
                this.reuses.fetch();
                this.issues.fetch();
                this.discussions.fetch();
            }
        }
    },
};
</script>
