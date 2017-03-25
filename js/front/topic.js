/**
 * Topic display page JS module
 */
import FrontMixin from 'front/mixin';

import log from 'logger';
import Vue from 'vue';

new Vue({
    mixins: [FrontMixin],
    ready() {
        log.debug('Topic display page');
    }
});
