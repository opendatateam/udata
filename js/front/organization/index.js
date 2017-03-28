/**
 * Organization display page JS module
 */
import FrontMixin from 'front/mixin';

import log from 'logger';

import Vue from 'vue';

import Tabset from 'vue-strap/src/Tabset.vue';

import FollowButton from 'components/buttons/follow.vue';
import ActivityTimeline from 'components/activities/timeline.vue';
import DashboardGraphs from 'components/dashboard/graphs.vue';
import Tab from 'components/tab';

import SmallBox from 'components/containers/small-box.vue';

import MembershipRequest from './membership-request.vue';

// Ensure retrocompatibily for 0.12.2 replace behavior
Vue.options.replace = false;


new Vue({
    mixins: [FrontMixin],
    components: {FollowButton, Tab, Tabset, ActivityTimeline, DashboardGraphs, SmallBox},
    data() {
        return {
            followersVisible: false,
            // Current tab index
            currentTab: 0,
        };
    },
    methods: {
        /**
        * Display the membership request modal
        */
        requestMembership(url) {
            this.$auth(this._('You need to be logged in to request membership to an organization'));
            this.$modal(MembershipRequest, {url});
        },
        showFollowers() {
            this.followersVisible = true;
        }
    },
    ready() {
        log.debug('Organization display page');

        // Restore tab from hash
        if (location.hash !== '') {
            this.$refs.tabs.$children.some((tab, index) => {
                if (`#${tab.id}` === location.hash) {
                    this.currentTab = index;
                    return true;
                }
            });
        }
    },
    watch: {
        /**
        * Set current tab ID as location hash
        * @param  {Number} index The new tab index
        */
        currentTab(index) {
            location.hash = this.$refs.tabs.$children[index].id;
        }
    }
});
