<template>
    <span :class="['label', checkAvailability.class]">{{ checkAvailability.message }}</span>
</template>

<script>
export default {
    name: 'availability-from-status',
    props: {
        status: {
            type: Number,
            required: true,
        }
    },
    computed: {
        checkAvailability() {
            if (this.status >= 200 && this.status < 400) {
                return {
                    message: this._('Available'),
                    class: 'label-success'
                }
            } else if (this.status >= 400 && this.status < 500) {
                return {
                    message: this._('Unavailable'),
                    class: 'label-danger'
                }
            } else if (this.status >= 500) {
                return {
                    message: this._('Unavailable (maybe temporary)'),
                    class: 'label-warning'
                }
            }
        },
    }
}
</script>
