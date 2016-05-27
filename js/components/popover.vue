<template>
<div class="popover" :class="classes" v-show="show" :style="style" :transition="effect">
    <div class="arrow"></div>
    <h3 class="popover-title" v-show="title">{{title}}</h3>
    <div class="popover-content" v-el:content>{{content}}</div>
</div>
</template>
<script>
import log from 'logger';

export default {
    props: {
        // The target element triggering the tooltip
        target: null,
        // The eefect used on tooltip apparition
        effect: {type: String, default: 'scale'},
        // An optionnal title
        title: [String, Element, HTMLElement],
        // The tooltip content
        content: [String, Element, HTMLElement],
        // The tooltip position (relative to the trigger element)
        placement: {type: String, default: 'top'},
        // Wider popover
        large: {type: Boolean, default: false},
    },
    data() {
        return {
            show: false
        }
    },
    computed: {
        classes() {
            const classes = {large: this.large};
            classes[this.placement] = true;
            return classes;
        },
        style() {
            return {
                top: `${this.position.top}px`,
                left: `${this.position.left}px`,
            }
        },
        position() {
            // Ensure position is refreshed on change
            if (!this.placement || !this.target || !this.show || !this.content) return {top: 0, left: 0};

            const box = this.target.getBoundingClientRect();
            const width = this.$el.offsetWidth;
            const height = this.$el.offsetHeight;

            switch (this.placement) {
                case 'top':
                    return {
                        left: window.pageXOffset + box.left - this.$el.offsetWidth / 2 + box.width / 2,
                        top: window.pageYOffset + box.top - this.$el.offsetHeight,
                    };
                case 'left':
                    return {
                        left: window.pageXOffset + box.left - this.$el.offsetWidth,
                        top: window.pageYOffset + box.top + box.height / 2 - this.$el.offsetHeight / 2,
                    };
                case 'right':
                    return {
                        left: window.pageXOffset + box.left + box.width,
                        top: window.pageYOffset + box.top + box.height / 2 - this.$el.offsetHeight / 2,
                    };
                case 'bottom':
                    return {
                        left: window.pageXOffset + box.left - this.$el.offsetWidth / 2 + box.width / 2,
                        top:  window.pageYOffset + box.top + box.height,
                    };
                default:
                    log.error(`Unknown placement: ${this.placement}`);
                    return {top: -1000, left: -1000};
            }
        }
    },
    methods: {
        toggle() {
            this.show = !this.show
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
