<template>
<div class="tooltip" :class="[placement]" v-show="show" :style="style"
    :transition="effect" role="tooltip">
    <div class="tooltip-arrow"></div>
    <div class="tooltip-inner">{{content}}</div>
</div>
</template>
<script>
import TooltipMixin from 'mixins/tooltip';

import 'vue-strap/src/Tooltip.vue'; // Needed for style

export default {
    name: 'tooltip',
    mixins: [TooltipMixin],
    props: {
        // The tooltip content
        content: String,
    }
}
</script>

<style lang="less">
// Rely on vue-strap tooltip style
</style>
