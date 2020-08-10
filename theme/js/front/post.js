/**
 * Post display page JS module
 */
import FrontMixin from 'front/mixin';

import log from 'logger';

import Vue from 'vue';

import 'less/post.less';

// Components
import ShareButton from 'components/buttons/share.vue';
import DiscussionThreads from 'components/discussions/threads.vue';


new Vue({
    mixins: [FrontMixin],
    components: {ShareButton, DiscussionThreads},
    ready() {
        log.debug('Post page ready');
    }
});
