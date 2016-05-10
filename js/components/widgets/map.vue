<style lang="less">
.map-widget {
    .box-body {
        height: 350px;
    }

    .leaflet-popup {
        color: black;
    }

    .box-footer {
        ul {
            list-style: none;
            margin: 0;
            padding: 0;

            li {
                display: inline-block;
                padding: 0;

                a {
                    color: #fff;
                }
            }
        }
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
        <leaflet-map class="box-body no-padding" :geojson="geojson"></leaflet-map>
        <div class="box-footer bg-light-blue-gradient text-center" v-show="footer">
            <slot></slot>
        </div>
    </div>
</template>

<script>
import LeafletMap from '../leaflet-map.vue';

export default {
    props: {
        title: String,
        icon: {
            type: String,
            default: 'globe'
        },
        footer: Boolean,
        geojson: null
    },
    components: {LeafletMap}
};
</script>
