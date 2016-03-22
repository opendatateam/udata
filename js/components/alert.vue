<template>
    <div class="alert fade" :class="classes">
        <button type="button" class="close" aria-hidden="true" @click="close">×</button>
        <h4>
            <span class="icon fa fa-{{alert.icon || 'check'}}"></span>
            {{alert.title}}
        </h4>
        {{alert.details}}
    </div>
</template>

<script>
const TRANSITION_DURATION = 300;

export default {
    name: 'alert-box',
    replace: true,
    data() {
        return {
            closing: false
        };
    },
    props: {
        alert: Object
    },
    computed: {
        closable() {
            return this.alert.closable === undefined ? true : this.alert.closable;
        },
        classes() {
            const classes = {
                'alert-dismissable': this.closable,
                'in': !this.closing,
            };
            classes[`alert-${this.alert.type || 'success'}`] = true;
            return classes;
        }
    },
    methods: {
        close() {
            this.closing = true;
            setTimeout(() => {
                this.$dispatch('notify:close', this.alert);
            }, TRANSITION_DURATION)
        }
    }
};
</script>
