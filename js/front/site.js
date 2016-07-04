/**
 * Generic site display page JS module
 */
import 'front/bootstrap';

import log from 'logger';
import Vue from 'vue';

new Vue({
    el: 'body',
    ready() {
        log.debug('Site page');
    }
});
