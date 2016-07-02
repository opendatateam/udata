// ES6 environment
import 'front/bootstrap';

import Vue from 'vue';
import API from 'api';

import ActivityTimeline from 'components/activities/timeline.vue';
import DashboardGraphs from 'components/dashboard/graphs.vue';

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;

API.onReady(function() {
    new Vue({
        components: {ActivityTimeline, DashboardGraphs}
    });
});
