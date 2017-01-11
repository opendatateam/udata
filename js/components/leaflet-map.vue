<template>
<div></div>
</template>
<script>
import L from 'leaflet';
import config from 'config';

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

        L.tileLayer(config.tiles_url, config.tiles_config).addTo(this.map);
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
