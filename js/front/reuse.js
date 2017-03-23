/**
 * Reuse display page JS module
 */
import 'front/bootstrap';

import log from 'logger';

// Legacy widgets
import 'widgets/issues-btn';

import Vue from 'vue';

import FrontMixin from 'front/mixin';

// Components
import FollowButton from 'components/buttons/follow.vue';
import ShareButton from 'components/buttons/share.vue';
import FeaturedButton from 'components/buttons/featured.vue';
import DiscussionThreads from 'components/discussions/threads.vue';

new Vue({
    mixins: [FrontMixin],
    components: {FollowButton, ShareButton, DiscussionThreads, FeaturedButton},
    ready() {
        log.debug('Reuse display page');
    },
    methods: {
        /**
         * Suggest a tag aka.trigger a new discussion
         */
        suggestTag() {
            this.$refs.discussions.start(
                this._('New tag suggestion to improve metadata'),
                this._('Hello,\n\nI propose this new tag: ')
            );
        }
    }
});
