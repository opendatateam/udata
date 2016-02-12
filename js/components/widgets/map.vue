<style lang="less">
.map-widget {
    .box-body {
        height: 350px;
    }

    .leaflet-popup {
        color: black;
    }
}
</style>

<template>
    <div class="box box-solid bg-light-blue-gradient map-widget">
        <header class="box-header" v-show="title || icon">
            <i v-show="icon" class="fa fa-{{icon}}"></i>
            <h3 class="box-title">{{title}}</h3>
            <div class="box-tools"></div>
        </header>
        <div class="box-body no-padding" v-el:container></div>
    </div>
</template>

<script>
import L from 'leaflet';

const ATTRIBUTIONS = [
        '&copy;',
        '<a href="http://openstreetmap.org">OpenStreetMap</a>',
        '/',
        '<a href="http://open.mapquest.com/">MapQuest</a>'
    ].join(' '),
    TILES_PREFIX = location.protocol === 'https:' ? '//otile{s}-s' : '//otile{s}',
    TILES_URL = TILES_PREFIX + '.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
    TILES_CONFIG = {subdomains: '1234', attribution: ATTRIBUTIONS},
    INITIAL_SETTINGS = {center: [42, 2.4], zoom: 4, zoomControl: false};

export default {
    props: {
        title: String,
        icon: {
            type: String,
            default: 'globe'
        },
        // Whether or not to allow zooming and paning (scrool, tap...)
        fixed: {
            type: Boolean,
            default: true
        },
        geojson: null
    },
    ready: function() {
        this.map = L.map(this.$els.container, INITIAL_SETTINGS);

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
        'geojson': function(json) {
            if (json) {
                this.layer = L.geoJson(json, {
                    onEachFeature: function (feature, layer) {
                        if (feature.properties && feature.properties.name) {
                            layer.bindPopup(feature.properties.name);
                            layer.on("mouseover", function () {
                                layer.openPopup();
                            });
                            layer.on("mouseout", function () {
                                layer.closePopup();
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
