<template>
    <div class="alert fade" :class="classes">
        <button type="button" class="close" aria-hidden="true" @click="close">×</button>
        <h4>
            <span class="icon fa fa-{{alert.icon || 'check'}}"></span>
            {{alert.title}}
        </h4>
        {{{ details | markdown }}}
    </div>
</template>

<script>
const TRANSITION_DURATION = 300;
const AUTOCLOSE_DELAY = 5000;

export default {
    name: 'alert-box',
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
        },
        details() {
            if (this.alert && this.alert.details) {
                return this.alert.details;
            }
        }
    },
    methods: {
        close() {
            this.closing = true;
            setTimeout(() => {
                this.$dispatch('notify:close', this.alert);
            }, TRANSITION_DURATION)
        }
    },
    ready() {
        if (this.alert.autoclose) {
            setTimeout(() => {
                this.$dispatch('notify:close', this.alert)
            }, AUTOCLOSE_DELAY);
        }
    }
};
</script>
