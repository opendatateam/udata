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
    v-style="width:size+'px', height:size+'px'"
    v-on="click: click">
    <img v-attr="src:src" />
    <small class="change-overlay">{{ _('change') }}</small>
</div>
</template>

<script>
import Vue from 'vue';

export default {
    data: function() {
        return {
            src: null,
            size: 100,
            endpoint: null,
            sizes: [100]
        };
    },
    props: ['src', 'size', 'sizes', 'endpoint'],
    methods: {
        click: function() {
            this.$root.$modal(
                {data: {endpoint: this.endpoint, sizes: this.sizes}},
                Vue.extend(require('components/widgets/image-picker-modal.vue'))
            ).$once('image:saved', () => {
                this.$dispatch('image:saved');
            });
        }
    }
};
</script>
