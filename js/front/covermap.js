/**
 * Coverage map page JS module
 */
import 'front/bootstrap';

import Vue from 'vue';

import log from 'logger';

// Legacy widgets
import Map from 'dashboard/map';

new Vue({
    el: 'body',
    ready() {
        log.debug('Loading map');
        const map = new Map('.big-map');
        map.load();
    }
});
