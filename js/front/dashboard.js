// ES6 environment
import FrontMixin from 'front/mixin';

import 'less/dashboard.less';

import Vue from 'vue';

import ActivityTimeline from 'components/activities/timeline.vue';
import SmallBox from 'components/containers/small-box.vue';
import DashboardGraphs from 'components/dashboard/graphs.vue';


new Vue({
    mixins: [FrontMixin],
    components: {ActivityTimeline, DashboardGraphs, SmallBox},
});
