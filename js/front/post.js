/**
 * Post display page JS module
 */
import FrontMixin from 'front/mixin';

import log from 'logger';

import Vue from 'vue';

// Components
import ShareButton from 'components/buttons/share.vue';


new Vue({
    mixins: [FrontMixin],
    components: {ShareButton},
    ready() {
        log.debug('Post page ready');
    }
});
