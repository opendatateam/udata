<template>
<div class="popover" :class="classes" v-show="show" :style="style" :transition="effect">
    <div class="arrow"></div>
    <h3 class="popover-title" v-show="title">{{title}}</h3>
    <div class="popover-content" v-el:content>{{content}}</div>
</div>
</template>
<script>
import log from 'logger';
import TooltipMixin from 'mixins/tooltip';

import 'vue-strap/src/Popover.vue'; // Needed for style

export default {
    name: 'popover',
    mixins: [TooltipMixin],
    props: {
        // An optional title
        title: [String, Element, HTMLElement],
        // The popover content
        content: [String, Element, HTMLElement],
        // Wider popover
        large: {type: Boolean, default: false},
        extraclass: String,
    },
    computed: {
        classes() {
            const classes = {large: this.large};
            classes[this.placement] = true;
            if (this.extraclass) classes[this.extraclass] = true;
            return classes;
        }
    },
    watch: {
        /**
         * Transclude content if necessary
         */
        content(value) {
            if (value instanceof HTMLElement) {
                this.$els.content.innerHTML = '';
                this.$els.content.appendChild(value);
            }
        }
    }
}
</script>

<style lang="less">
// Rely on vue-strap popover style
</style>
