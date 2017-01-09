/**
 * Reuse display page JS module
 */
import 'front/bootstrap';

import log from 'logger';

// Legacy widgets
import 'widgets/issues-btn';
import 'widgets/discussions-btn';

import Vue from 'vue';

import FollowButton from 'components/buttons/follow.vue';
import ShareButton from 'components/buttons/share.vue';
import FeaturedButton from 'components/buttons/featured.vue';


new Vue({
    el: 'body',
    components: {FollowButton, ShareButton, FeaturedButton},
    ready() {
        log.debug('Reuse display page');
    }
});
