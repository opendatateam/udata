<template>
<div></div>
</template>
<script>
import L from 'leaflet';

const ATTRIBUTIONS = `&copy;<a href="http://openstreetmap.org">OpenStreetMap</a>
                      /<a href="http://open.mapquest.com/">MapQuest</a>`;
const TILES_PREFIX = location.protocol === 'https:' ? '//otile{s}-s' : '//otile{s}';
const TILES_URL = TILES_PREFIX + '.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png';
const TILES_CONFIG = {subdomains: '1234', attribution: ATTRIBUTIONS};
const INITIAL_SETTINGS = {center: [42, 2.4], zoom: 4, zoomControl: false};

export default {
    replace: true,
    props: {
        // Whether or not to allow zooming and paning (scrool, tap...)
        fixed: {
            type: Boolean,
            default: true
        },
        // Whetjer or not to display hover popup
        popup: {
            type: Boolean,
            default: true
        },
        geojson: null
    },
    ready() {
        this.map = L.map(this.$el, INITIAL_SETTINGS);

        if (this.fixed) {
            // Disable drag and zoom handlers.
            this.map.dragging.disable();
            this.map.touchZoom.disable();
            this.map.doubleClickZoom.disable();
            this.map.scrollWheelZoom.disable();

            // Disable tap handler, if present.
            if (this.map.tap) this.map.tap.disable();
        }

        L.tileLayer(TILES_URL, TILES_CONFIG).addTo(this.map);
    },
    watch: {
        geojson: function(json) {
            if (json) {
                this.layer = L.geoJson(json, {
                    onEachFeature: (feature, layer) => {
                        if (this.popup && feature.properties && feature.properties.name) {
                            layer.bindPopup(feature.properties.name);
                            layer.on('mouseover', () => layer.openPopup());
                            layer.on('mouseout', () => {
                                if (layer.closePopup) {
                                    layer.closePopup();
                                } else {
                                    layer.eachLayer(layer => layer.closePopup());
                                }
                            });
                        }
                    }
                });
                this.layer.addTo(this.map);
                this.map.fitBounds(this.layer.getBounds());
            }
        }
    }
};
</script>
<style lang="less"></style>
