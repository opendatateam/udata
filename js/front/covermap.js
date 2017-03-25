/**
 * Coverage map page JS module
 */
import FrontMixin from 'front/mixin';

import Vue from 'vue';

import log from 'logger';

// Legacy widgets
import Map from 'dashboard/map';

new Vue({
    mixins: [FrontMixin],
    ready() {
        log.debug('Loading map');
        const map = new Map('.big-map');
        map.load();
    }
});
