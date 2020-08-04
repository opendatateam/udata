/**
 * Organization display page JS module
 */
import 'less/front/organization.less';

import FrontMixin from 'front/mixin';

import log from 'logger';

import Vue from 'vue';

// import Tabset from 'vue-strap/src/Tabset.vue';

import FollowButton from 'components/buttons/follow.vue';
import DetailsModal from './details-modal.vue';
import ActivityTimeline from 'components/activities/timeline.vue';
import Tab from 'components/tab';
import Tabset from 'components/tabs.vue';

import SmallBox from 'components/containers/small-box.vue';

import MembershipRequest from './membership-request.vue';


new Vue({
    mixins: [FrontMixin],
    components: {FollowButton, Tab, Tabset, ActivityTimeline, SmallBox},
    data() {
        return {
            organization: this.extractOrganization(),
            followersVisible: false,
            // Current tab index
            currentTab: 0,
            // URL hash value
            hash: undefined,
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
        },
        /**
         * Extract the current organization metadatas from JSON-LD script
         * @return {Object} The parsed organization
         */
        extractOrganization() {
            const selector = '#json_ld';
            const organization = JSON.parse(document.querySelector(selector).text);

            return organization;
        },

        /**
         * Display the details modal
         */
        showDetails() {
            this.$modal(DetailsModal, {organization: this.organization});
        }

    },
    ready() {
        log.debug('Organization display page');

        // Restore tab from hash
        if (location.hash !== '') {
            this.hash = location.hash;
        }
        // Keep tab in sync with URL hash
        window.addEventListener('hashchange', () => {
            this.hash = location.hash;
        });
    },
    watch: {
        /**
        * Set current tab ID as location hash
        * @param  {Number} index The new tab index
        */
        currentTab(index) {
            location.hash = this.$refs.tabs.$children[index].id;
        },
        hash(hash) {
            this.$refs.tabs.$children.some((tab, index) => {
                if (`#${tab.id}` === hash) {
                    this.currentTab = index;
                    return true;
                }
            });
        }
    },
});
