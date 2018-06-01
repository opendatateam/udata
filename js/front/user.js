/*
 * User display page
 */
import 'less/front/user.less';

import FrontMixin from 'front/mixin';

import log from 'logger';

import Vue from 'vue';

import Tabset from 'vue-strap/src/Tabset.vue';

import FollowButton from 'components/buttons/follow.vue';
import ActivityTimeline from 'components/activities/timeline.vue';
import Tab from 'components/tab';

new Vue({
    mixins: [FrontMixin],
    components: {FollowButton, Tab, Tabset, ActivityTimeline},
    data() {
        return {
            // Current tab index
            currentTab: 0,
        };
    },
    ready() {
        log.debug('User display page');

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
        },
    }
});
