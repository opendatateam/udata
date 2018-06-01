/**
 * Reuse display page JS module
 */
import 'less/front/reuse.less';

import FrontMixin from 'front/mixin';

import log from 'logger';

import Vue from 'vue';

// Components
import DiscussionThreads from 'components/discussions/threads.vue';
import FeaturedButton from 'components/buttons/featured.vue';
import FollowButton from 'components/buttons/follow.vue';
import IntegrateButton from 'components/buttons/integrate.vue';
import IssuesButton from 'components/buttons/issues.vue';
import ShareButton from 'components/buttons/share.vue';

new Vue({
    mixins: [FrontMixin],
    components: {
        FollowButton, ShareButton, DiscussionThreads, FeaturedButton, IssuesButton, IntegrateButton
    },
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
