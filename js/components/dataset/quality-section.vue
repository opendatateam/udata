<template>
<div>
    <h3 class="pointer" :class="textClass" @click="toggle">
        <span class="fa" :class="iconClass"></span>
        {{ title }}
    </h3>
    <div class="collapse" :class="contentClass">
        <slot></slot>
        <p :class="textClass">
            <strong v-if="condition && !showInfo">{{ ok }}</strong>
            <strong v-if="!condition && !showInfo">{{ ko }}</strong>
            <strong v-if="showInfo">{{ info }}</strong>
        </p>
    </div>
</div>
</template>
<script>
export default {
    props: {
        title: String,
        condition: [Boolean, null],
        ok: String,
        ko: String,
        info: [String, null],
        showInfo: {
            type: Boolean,
            default: false
        },
    },
    data() {
        return {
            toggled: null
        }
    },
    computed: {
        expanded() {
            return this.toggled === null ? !this.condition || this.showInfo : this.toggled;
        },
        contentClass() {
            return {
                in: this.expanded
            };
        },
        iconClass() {
            return {
                'fa-check-circle': this.condition && !this.showInfo,
                'fa-exclamation-circle': !this.condition && !this.showInfo,
                'fa-question-circle': this.showInfo,
            };
        },
        textClass() {
            return {
                'text-success': this.condition && !this.showInfo,
                'text-warning': !this.condition && !this.showInfo,
                'text-info': this.showInfo,
            };
        }
    },
    methods: {
        toggle() {
            this.toggled = !this.expanded;
        }
    }
};
</script>
