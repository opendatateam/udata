/**
 * Reuse display page JS module
 */
// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import log from 'logger';
import Vue from 'vue';

new Vue({
    el: 'body',
    ready() {
        log.debug('Topic display page');
    }
});
