/**
 * Dataset display page JS module
 */
// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import Vue from 'vue';
import config from 'config';
import log from 'logger';

// Components
import LeafletMap from 'components/leaflet-map.vue';

Vue.config.debug = config.debug;

Vue.use(require('plugins/api'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/i18next'));


new Vue({
    el: 'body',
    components: {LeafletMap},
    ready() {
        this.loadMap();
        log.debug('Territory page ready');
    },
    methods: {
        /**
         * Load map data if required
         */
        loadMap() {
            if (!this.$refs.map) return;
            this.$http.get(this.$refs.map.$el.dataset.zones).then(response => {
                this.$refs.map.geojson = response.data;
            });
        }
    }
});
