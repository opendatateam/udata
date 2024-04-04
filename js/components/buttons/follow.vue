<template>
<button type="button" class="btn btn-follow" :class="btnClasses" @click="toggle"
    v-tooltip="tooltip" :tooltip-placement="tooltipPlacement">
    <span class="fa" :class="icon"></span>
    <span v-if="withLabel">{{ label }}</span>
    <span v-if="followers">{{ followers }}</span>
</button>
</template>

<script>
import i18n from 'i18n';

export default {
    props: {
        classes: {
            type: Array,
            coerce(value) {
                if (Array.isArray(value)) return value;
                return value.split(' ').filter(value => value.trim());
            }
        },
        followers: {
            type: Number,
            default: undefined
        },
        following: {
            type: Boolean,
            default: false
        },
        withLabel: {
            type: Boolean,
            default: false
        },
        tooltip: {
            type: String,
            default: i18n._("I'll be informed about its activity")
        },
        tooltipPlacement: {
            type: String,
            default: 'left'
        },
        url: {
            type: String,
            required: true
        }
    },
    computed: {
        btnClasses() {
            const classes = {active: this.following};
            this.classes.forEach(cls => {
                classes[cls] = true;
            });
            return classes;
        },
        icon() {
            return this.following ? 'fa-star': 'fa-star-o';
        },
        label() {
            return this.following ? this._('Unfollow') : this._('Follow');
        }
    },
    methods: {
        toggle() {
            this.$auth(this._('You need to be logged in to follow.'));
            const method = this.following ? this.$api.delete(this.url) : this.$api.post(this.url);
            method.then(data => {
                this.following = !this.following;
                if (this.followers !== undefined) {
                    this.followers = data.followers;
                }
            });
        }
    }
};
</script>

<style lang="less"></style>
