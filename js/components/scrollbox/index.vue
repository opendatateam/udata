<!--
    A scrollbox component based on:
    - https://github.com/BosNaufal/vue-scrollbar
    - https://github.com/kamlekar/slim-scroll

    It provides the following features (some are broken on above components):
    - slim scrollbars (customizable)
    - over effect (also customizable)
    - proper touch and wheel support
    - handle resize and manual refresh
    - jump on click on the scrollbar container
    - events on nested components properly propagate
    - parent size/style is taken in account (padding/margin)
    - takes advantages of Vue.js

    NB: This could be packaged as a standalone reusable component.
-->
<template>
<div v-el:wrapper class="scrollbox__wrapper" :class="{dragging: dragging}">
    <div v-el:area class="scrollbox__area"
        @wheel.prevent="onScroll"
        @touchstart.stop="startDrag"
        @touchmove="onDrag" @touchend="stopDrag"
        :style="{'margin-top': `${top * -1}px`, 'margin-left': `${left * -1}px` }">
        <slot></slot>
    </div>
    <vertical-scrollbar v-if="canScrollY" v-ref:vscrollbar></vertical-scrollbar>
    <horizontal-scrollbar v-if="canScrollX" v-ref:hscrollbar></horizontal-scrollbar>
</div>
</template>

<script>
import VerticalScrollbar from './vertical-scrollbar.vue';
import HorizontalScrollbar from './horizontal-scrollbar.vue';

export default {
    name: 'scrollbox',
    props: {
        speed: {type: Number, default: 53},
    },

    data() {
        return {
            area: {height: null, width: null},
            wrapper: {height: null, width: null},
            start: {y: 0, x: 0},
            movement: {x: 0, y: 0},
            scroll: {x: null, y: null},
            dragging: false,
        };
    },

    components: {VerticalScrollbar, HorizontalScrollbar},

    computed: {
        canScrollY() {
            return this.area.height > this.wrapper.height;
        },
        canScrollX() {
            return this.area.width > this.wrapper.width;
        },
        top() {
            return this.movement.y * this.area.height / 100;
        },
        left() {
            return this.movement.x * this.area.width / 100;
        }
    },

    methods: {
        onScroll(e) {
            // DOM events
            const shifted = e.shiftKey;
            this.scroll.y = e.deltaY > 0 ? this.speed : -(this.speed);
            this.scroll.x = e.deltaX > 0 ? this.speed : -(this.speed);

            // Fix Mozilla Shifted Wheel~
            if (shifted && e.deltaX == 0) this.scroll.x = e.deltaY > 0 ? this.speed : -(this.speed);

            // Next Value
            const nextY = this.top + this.scroll.y;
            const nextX = this.left + this.scroll.x;

            // Vertical Scrolling
            if (this.canScrollY && !shifted) {
                this.moveVertical(nextY);
            }

            // Horizontal Scrolling
            if (shifted && this.canScrollX) {
                this.moveHorizontal(nextX);
            }

        },

        // DRAG EVENT JUST FOR TOUCH DEVICE~
        startDrag(e) {
            e = e.changedTouches ? e.changedTouches[0] : e;

            // Prepare to drag
            this.dragging = true;
            this.start.y = e.pageY;
            this.start.x = e.pageX;
        },

        onDrag(e) {
            if (this.dragging) {
                e.preventDefault();
                e = e.changedTouches ? e.changedTouches[0] : e;

                // Invers the Movement
                const yMovement = this.start.y - e.pageY;
                const xMovement = this.start.x - e.pageX;

                // Update the last e.page
                this.start.y = e.pageY;
                this.start.x = e.pageX;

                // The next Vertical Value will be
                const nextY = this.top + yMovement;
                const nextX = this.left + xMovement;

                if (this.canScrollY) this.moveVertical(nextY);
                if (this.canScrollX) this.moveHorizontal(nextX);
            }
        },

        stopDrag(e) {
            this.dragging = false;
        },

        moveVertical(next) {
            const normalized = next * 100 / this.area.height;
            this.$refs.vscrollbar.move(normalized);
        },

        moveHorizontal(next) {
            const normalized = next * 100 / this.area.width;
            this.$refs.hscrollbar.move(normalized);
        },

        calculateSize() {
            // Computed Style
            const style = window.getComputedStyle(this.$els.wrapper, null);

            // Scroll Area Height and Width
            this.area.height = this.$els.area.children[0].clientHeight;
            this.area.width = this.$els.area.children[0].clientWidth;

            // Scroll Wrapper Height and Width
            this.wrapper.height = parseFloat(style.height);
            this.wrapper.width = parseFloat(style.width);
        }
    },

    ready() {
        this.calculateSize();
        // Attach The Event for Responsive View~
        window.addEventListener('resize', this.calculateSize);
    },

    beforeDestroy() {
        // Remove Event
        window.removeEventListener('resize', this.calculateSize);
    }
};
</script>

<style lang="less">
.scrollbox {
    &__wrapper {
        margin: 0 auto;
        overflow: hidden;
        position: relative;

        &:hover,
        &.dragging {
            .scrollbox {
                &__scrollbar-horizontal,
                &__scrollbar-vertical {
                    opacity: 1;

                    .scrollbar {
                        opacity: 1;
                    }
                }
            }
        }
    }

    &__scrollbar-horizontal,
    &__scrollbar-vertical {
        transition: all 0.5s ease;
        cursor: pointer;
        opacity: 0.5;
        position: absolute;
        background: transparent;
        user-select: none;

        &:hover {
            background: rgba(0,0,0,0.5);
        }

        .scrollbar {
            transition: all 0.5s ease;
            opacity: 0.5;
            position: relative;
            background-color: #ccc;
        }
    }

    &__scrollbar-vertical {
        width: 5px;
        height: 100%;
        top: 0;
        right: 0;

        .scrollbar {
            width: 5px;
        }
    }

    &__scrollbar-horizontal {
        height: 5px;
        width: 100%;
        bottom: 0;
        right: 0;

        .scrollbar {
            height: 5px;
        }
    }
}
</style>
