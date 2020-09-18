<template>
<div v-el:container v-if="width < 100" @click="jump"
    class="scrollbox__scrollbar-horizontal">
    <div v-el:scrollbar class="scrollbar"
        :style="{width: `${width}%`, left: `${$parent.movement.x}%`}"
        @touchstart.prevent.stop="startDrag"
        @mousedown.prevent.stop="startDrag">
    </div>
</div>
</template>

<script>
export default {
    name: 'horizontal-scrollbar',

    data() {
        return {
            width: 0,
            start: 0,
        };
    },

    methods: {
        startDrag(e) {
            e = e.changedTouches ? e.changedTouches[0] : e;

            // Prepare to drag
            this.$parent.dragging = true;
            this.start = e.pageX;
        },

        onDrag(e) {
            if (this.$parent.dragging) {
                e.preventDefault();
                e.stopPropagation();

                e = e.changedTouches ? e.changedTouches[0] : e;

                const xMovement = e.pageX - this.start;
                const xMovementPercentage = xMovement / this.$parent.wrapper.width * 100;

                // Update the last e.pageX
                this.start = e.pageX;

                // The next Horizontal Value will be
                const next = this.$parent.movement.x + xMovementPercentage;

                this.move(next);
            }
        },

        stopDrag(e) {
            this.$parent.dragging = false;
        },

        jump(e) {
            const isContainer = e.target === this.$els.container;
            if (isContainer) {
                // Get the Element Position
                const position = this.$els.scrollbar.getBoundingClientRect();

                // Calculate the horizontal Movement
                const xMovement = e.pageX - position.left;

                const centerize = (this.width / 2);
                const xMovementPercentage = xMovement / this.$parent.wrapper.width * 100 - centerize;

                // Update the last e.pageX
                this.start = e.pageX;

                // The next horizontal Value will be
                const next = this.$parent.movement.x + xMovementPercentage;

                this.move(next);
            }
        },

        move(next) {
            // Check For the Max Position
            const lowerEnd = 100 - this.width;
            if (next < 0) next = 0;
            if (next > lowerEnd) next = lowerEnd;
            this.$parent.movement.x = next;
        },

        calculateSize() {
            // Scrollbar Width
            this.width = this.$parent.wrapper.width / this.$parent.area.width * 100;
        }
    },

    ready() {
        this.calculateSize()
        // Attach the Listener
        document.addEventListener("mousemove", this.onDrag);
        document.addEventListener("touchmove", this.onDrag);
        document.addEventListener("mouseup", this.stopDrag);
        document.addEventListener("touchend", this.stopDrag);
    },

    beforeDestroy() {
        // Remove the Listener
        document.removeEventListener("mousemove", this.onDrag);
        document.removeEventListener("touchmove", this.onDrag);
        document.removeEventListener("mouseup", this.stopDrag);
        document.removeEventListener("touchend", this.stopDrag);
    },

    watch: {
        '$parent.wrapper.width' (val, old) {
            if (val != old) this.calculateSize();
        }
    }
};
</script>
