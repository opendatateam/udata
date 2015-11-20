<style lang="less">
.image-button {
    @overlay-color: lighten(black, 40%);

    position: relative;

    img {
        height: 100%;
        width: 100%;
    }

    .change-overlay {
        position: absolute;
        display: none;
        top: 0;
        left: 0;
        color:white;
        padding: 0 5px;
        background-color: @overlay-color;
    }

    &:hover {
        border: 1px solid @overlay-color;
        background-color: lighten(@overlay-color, 30%);

        img {
            opacity: 0.5;
        }

        .change-overlay {
            display: block;
        }
    }

}
</style>

<template>
<div class="image-button pointer"
    :style="{width:size+'px', height:size+'px'}"
    @click="click">
    <img :src="src" />
    <small class="change-overlay">{{ _('change') }}</small>
</div>
</template>

<script>
import Vue from 'vue';

export default {
    props: {
        src: null,
        size: {
            type: Number,
            default: 100,
        },
        sizes: {
            type: Array,
            default: function() {return [100];}
        },
        endpoint: null
    },
    methods: {
        click: function() {
            this.$root.$modal(
                require('components/widgets/image-picker-modal.vue'),
                {endpoint: this.endpoint, sizes: this.sizes}
            ).$once('image:saved', () => {
                this.$dispatch('image:saved');
            });
        }
    }
};
</script>
