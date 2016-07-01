/*
 * User display page
 */
import 'front/bootstrap';

import log from 'logger';

import Vue from 'vue';

import {tabset} from 'vue-strap';

import FollowButton from 'components/buttons/follow.vue';
import ActivityTimeline from 'components/activities/timeline.vue';
import Tab from 'components/tab';

// TODO: simplify Swagger API handling for front views
import API from 'api';

// Legacy depedencies soon to be dropped
import $ from 'jquery';

$(API).on('built', function() {
    new Vue({
        el: 'body',
        components: {FollowButton, Tab, tabset, ActivityTimeline},
        data() {
            return {
                // Current tab index
                currentTab: 0,
                // API,
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
});
