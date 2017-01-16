/**
 * Dataset display page JS module
 */
import 'front/bootstrap';

import log from 'logger';

import Vue from 'vue';

// Components
import ShareButton from 'components/buttons/share.vue';


new Vue({
    el: 'body',
    components: {ShareButton},
    ready() {
        log.debug('Post page ready');
    }
});
