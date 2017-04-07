/**
 * Coverage map page JS module
 */
import FrontMixin from 'front/mixin';

import Vue from 'vue';

import log from 'logger';

import L from 'leaflet';
import 'leaflet-spin';

import LeafletMap from 'components/leaflet-map.vue';
import PopupOptions from './popup.vue';
import Spinner from 'spin.js';

const LETTERS = '0123456789ABCDEF'.split('');
const Popup = Vue.extend(PopupOptions);

if (!window.Spinner) { // Fix for leaflet.spin
    window.Spinner = Spinner;
}

function randomColor() {
    let color = '#';

    for (let i = 0; i < 6; i++) {
        color += LETTERS[Math.round(Math.random() * LETTERS.length)];
    }
    return color;
}

new Vue({
    mixins: [FrontMixin],
    components: {LeafletMap},
    data() {
        return {
            style: {
                clickable: true,
                weight: 0.5,
                opacity: 0.5,
                fillOpacity: 0.3
            },
            hoverStyle: {
                fillOpacity: 0.8
            },
            children: [],
            levels: []
        };
    },
    computed: {
        map() {
            return this.$refs.map.map;
        }
    },
    events: {
        drillDown(level, bounds) {
            this.bounds = bounds;
            this.map.fitBounds(bounds);
            this.switchLevel(level);
        }
    },
    ready() {
        this.map.spin(true);
        this.$api.get('spatial/levels').then(this.onLevelsLoaded);
        log.debug('Coverage map ready');
    },
    methods: {
        onLevelsLoaded(data) {
            const layers = {};

            this.levels = data.sort((a, b) => a.position - b.position).map(level => {
                level.dataUrl = `spatial/coverage/${level.id}`;
                level.layer = L.geoJson(null, {style: this.style, onEachFeature: this.onEachFeature});

                level.layer.level = level;
                layers[level.name] = level.layer;
                return level;
            });

            L.control.layers(layers, null, {collapsed: false}).addTo(this.map);
            this.map.on('baselayerchange', (ev) => {
                this.switchLevel(ev.layer.level);
            });

            this.switchLevel(this.levels[0]);
        },

        /**
         * Display a given level
         */
        switchLevel(level) {
            if (typeof level === 'string' || level instanceof String) {
                level = this.levels.find(l => l.id === level);
            }

            if (level.layer === this.layer) return;  // already set

            this.map.spin(true);

            this.children = this.levels.filter(l => l.parents.includes(level.id));

            if (this.layer && this.map.hasLayer(this.layer)) {
                this.map.removeLayer(this.layer);
            }
            this.layer = level.layer;
            if (!this.map.hasLayer(level.layer)) {
                level.layer.addTo(this.map);
            }

            if (!level.layer.loaded) {
                this.$api.get(level.dataUrl).then(data => {
                    level.layer.loaded = true;
                    this.layer.addData(data);
                    this.dataLoaded();
                });
            } else {
                this.dataLoaded();
            }
        },

        /**
         * End the loading state and center the map on the chosen bounds
         */
        dataLoaded() {
            this.map.fitBounds(this.bounds || this.layer.getBounds());
            while(this.map._spinner) {
                this.map.spin(false);
            }
            this.bounds = null;
        },

        /**
         * Apply style to each feature:
         */
        onEachFeature(feature, layer) {
            const baseColor = randomColor();
            const popup = new Popup({
                el: document.createElement('div'),
                parent: this,
                propsData: {feature, children: this.children, bounds: layer.getBounds()}
            });

            layer.setStyle(Object.assign({}, this.style, {
                color: baseColor,
                fillColor: baseColor
            }));

            layer.bindPopup(popup.$el);
            layer.on('mouseover', () => layer.setStyle(this.hoverStyle));
            layer.on('mouseout', () => layer.setStyle(this.style));
        }
    }
});
