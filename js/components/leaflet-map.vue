<template>
<div></div>
</template>
<script>
import L from 'leaflet';
import config from 'config';

export default {
    name: 'leaflet-map',
    props: {
        // Whether or not to allow zooming and paning (scrool, tap...)
        fixed: {
            type: Boolean,
            default: true
        },
        // Whether or not to display hover popup
        popup: {
            type: Boolean,
            default: true
        },
        geojson: null
    },
    ready() {
        this.map = L.map(this.$el, {
            center: config.map.init.center,
            zoom: config.map.init.zoom,
            zoomControl: false
        });

        if (this.fixed) {
            // Disable drag and zoom handlers.
            this.map.dragging.disable();
            this.map.touchZoom.disable();
            this.map.doubleClickZoom.disable();
            this.map.scrollWheelZoom.disable();

            // Disable tap handler, if present.
            if (this.map.tap) this.map.tap.disable();
        }

        const tiles_url = config.hidpi ? config.map.tiles.hidpi : config.map.tiles.url;
        L.tileLayer(tiles_url, config.map.tiles.config).addTo(this.map);
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
                const bounds = this.layer.getBounds();
                if (bounds.isValid()) this.map.fitBounds(bounds);
            }
        }
    }
};
</script>
<style lang="less"></style>
