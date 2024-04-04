<template>
<div>
<layout :title="_('Dashboard')">
    <div class="row">
        <small-box class="col-lg-3 col-xs-6" v-for="b in dataBoxes"
            :value="b.value" :label="b.label" :color="b.color"
            :icon="b.icon" :target="b.target">
        </small-box>
    </div>

    <div class="row">
        <reuse-list class="col-xs-12" :reuses="reuses"
            :title="_('Reuses about your data (including your organizations)')">
        </reuse-list>
    </div>

    <div class="row">
        <discussion-list id="discussions-widget" class="col-xs-12" :discussions="discussions"
            :title="_('Discussions about your data (including your organizations)')">
        </discussion-list>
    </div>
</layout>
</div>
</template>

<script>
import moment from 'moment';
import {PageList} from 'models/base';
import MyMetrics from 'models/mymetrics';
// Widgets
import Layout from 'components/layout.vue';
import SmallBox from 'components/containers/small-box.vue';
import ReuseList from 'components/reuse/list.vue';
import DiscussionList from 'components/discussions/list.vue';

export default {
    name: 'Home',
    data() {
        return {
            metrics: new MyMetrics(),
            reuses: new PageList({
                ns: 'me',
                fetch: 'my_org_reuses',
                mask: ReuseList.MASK.concat(['deleted'])
            }),
            discussions: new PageList({
                ns: 'me',
                fetch: 'my_org_discussions',
                mask: DiscussionList.MASK
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
                icon: 'recycle',
                color: 'teal',
            }];
        }
    },
    components: {
        SmallBox,
        DiscussionList,
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
                this.discussions.fetch();
            }
        }
    },
};
</script>
