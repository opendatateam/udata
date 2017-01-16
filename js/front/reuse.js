/**
 * Reuse display page JS module
 */
import 'front/bootstrap';

import log from 'logger';

// Legacy widgets
import 'widgets/issues-btn';

import Vue from 'vue';

import FollowButton from 'components/buttons/follow.vue';
import ShareButton from 'components/buttons/share.vue';
import FeaturedButton from 'components/buttons/featured.vue';
import DiscussionThreads from 'components/discussions/threads.vue';


new Vue({
    el: 'body',
    components: {FollowButton, ShareButton, DiscussionThreads, FeaturedButton},
    ready() {
        log.debug('Reuse display page');
    }
});
