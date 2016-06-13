/**
 * Organization display page JS module
 */
// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import log from 'logger';
import Auth from 'auth';
import i18n from 'i18n';

import Vue from 'vue';

import {tabset} from 'vue-strap';

import FollowButton from 'components/buttons/follow.vue';
import Tab from 'components/tab';

import MembershipRequest from './membership-request.vue';


Vue.use(require('plugins/i18next'));
Vue.use(require('plugins/api'));
Vue.use(require('plugins/tooltips'));

new Vue({
    el: 'body',
    components: {FollowButton, Tab, tabset},
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
            if (Auth.need_user(i18n._('You need to be logged in to request membership to an organization'))) {
                return new Vue({
                    mixins: [MembershipRequest],
                    el: this.$els.modal,
                    replace: false, // Needed while all components are not migrated to replace: true behavior
                    parent: this,
                    propsData: {url}
                });
            }
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

        // Async membership request
        // $('a.membership').click(function() {
        //     const $this = $(this);
        //     const api_url = $this.data('api');
        //
        //     if (!Auth.need_user(i18n._('You need to be logged in to request membership to an organization'))) {
        //         return false;
        //     }
        //
        //     const $modal = modal({
        //         title: i18n._('Membership request'),
        //         content: modal_tpl(),
        //         close_btn: i18n._('Cancel'),
        //         actions: [{
        //             label: i18n._('Send request'),
        //             classes: 'btn-success'
        //         }]
        //     });
        //
        //     $modal.find('.btn-success').click(function() {
        //         const data = {comment: $modal.find('#comment').val()};
        //         $modal.find('button').attr('disabled', true);
        //         API.post(api_url, data, function() {
        //             const msg = i18n._('A request has been sent to the administrators');
        //             Notify.success(msg);
        //             $this.remove();
        //             $('#pending-button').removeClass('hide');
        //         }).error(function(e) {
        //             const msg = i18n._('Error while requesting membership');
        //             Notify.error(msg);
        //             log.error(e.responseJSON);
        //         }).always(function() {
        //             $modal.modal('hide');
        //             $modal.find('button').attr('disabled', false);
        //         });
        //         return false;
        //     });
        //     return false;
        // });
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
