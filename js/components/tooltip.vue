<template>
<div class="tooltip" :class="[placement]" v-show="show" :style="style"
    :transition="effect" role="tooltip">
    <div class="tooltip-arrow"></div>
    <div class="tooltip-inner">{{content}}</div>
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
        // The tooltip content
        content: String,
        // The tooltip position (relative to the trigger element)
        placement: {type: String, default: 'top'}
    },
    data() {
        return {
            show: false
        }
    },
    computed: {
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
}
</script>

<style lang="less">
// Rely on vue-strap tooltip style
</style>
