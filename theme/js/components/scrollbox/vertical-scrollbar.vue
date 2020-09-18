<template>
<div v-el:container  v-if="height < 100" @click="jump"
    class="scrollbox__scrollbar-vertical">
    <div v-el:scrollbar class="scrollbar"
        :style="{height: `${height}%`, top: `${$parent.movement.y}%`}"
        @touchstart.prevent.stop="startDrag"
        @mousedown.prevent.stop="startDrag">
    </div>
</div>
</template>

<script>
export default {
    name: 'vertical-scrollbar',

    data() {
        return {
            height: 0,
            start: 0,
        };
    },

    methods: {
        startDrag(e) {
            e = e.changedTouches ? e.changedTouches[0] : e;

            // Prepare to drag
            this.$parent.dragging = true;
            this.start = e.pageY;
        },

        onDrag(e) {
            if (this.$parent.dragging) {
                e.preventDefault();
                e.stopPropagation();

                e = e.changedTouches ? e.changedTouches[0] : e;

                const yMovement = e.pageY - this.start;
                const yMovementPercentage = yMovement / this.$parent.wrapper.height * 100;

                // Update the last e.pageY
                this.start = e.pageY;

                // The next Vertical Value will be
                const next = this.$parent.movement.y + yMovementPercentage;

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

                // Calculate the vertical Movement
                const yMovement = e.pageY - position.top;
                const centerize = (this.height / 2);
                const yMovementPercentage = yMovement / this.$parent.wrapper.height * 100 - centerize;

                // Update the last e.pageY
                this.start = e.pageY;

                // The next Vertical Value will be
                const next = this.$parent.movement.y + yMovementPercentage;

                this.move(next);
            }
        },

        move(next) {
            // Check For the Max Position
            const lowerEnd = 100 - this.height;
            if (next < 0) next = 0;
            if (next > lowerEnd) next = lowerEnd;
            this.$parent.movement.y = next;
        },

        calculateSize() {
            // Scrollbar Height
            this.height = this.$parent.wrapper.height / this.$parent.area.height * 100;
        }
    },

    ready() {
        this.calculateSize();
        // attach the listener
        document.addEventListener("mousemove", this.onDrag);
        document.addEventListener("touchmove", this.onDrag);
        document.addEventListener("mouseup", this.stopDrag);
        document.addEventListener("touchend", this.stopDrag);
    },

    beforeDestroy() {
        // Remove the listener
        document.removeEventListener("mousemove", this.onDrag);
        document.removeEventListener("touchmove", this.onDrag);
        document.removeEventListener("mouseup", this.stopDrag);
        document.removeEventListener("touchend", this.stopDrag);
    },

    watch: {
        '$parent.wrapper.height' (val, old) {
            if (val != old) this.calculateSize();
        }
    }
};
</script>
