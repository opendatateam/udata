/**
 * Dataset display page JS module
 */
import 'front/bootstrap';

import Vue from 'vue';
import log from 'logger';

// Components
import LeafletMap from 'components/leaflet-map.vue';


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
            this.$api.get(this.$refs.map.$el.dataset.zones).then(data => {
                this.$refs.map.geojson = data;
            });
        }
    }
});
