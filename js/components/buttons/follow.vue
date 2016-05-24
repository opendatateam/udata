<template>
<tooltip effect="fadein" placement="left" :content="tooltip">
    <button type="button"
        class="btn btn-warning btn-follow btn-block btn-sm btn-left"
        :class="{'active': following}"
        @click="toggle">
        <span class="fa" :class="icon"></span>
        <span v-if="label">{{ label }}</span>
    </button>
</tooltip>
</template>

<script>
import i18n from 'i18n';
import Auth from 'auth';

import { tooltip } from 'vue-strap';

export default {
    components: {tooltip},
    props: {
        following: {
            type: Boolean,
            default: false
        },
        label: Boolean,
        tooltip: String,
        url: {
            type: String,
            required: true
        }
    },
    computed: {
        icon() {
            return this.following ? 'fa-eye-slash': 'fa-eye';
        },
        label() {
            return this.following ? this._('Unfollow') : this._('Follow');
        }
    },
    methods: {
        toggle() {
            if (!Auth.need_user(i18n._('You need to be logged in to follow.'))) {
                return;
            }
            const method = this.following ? this.$api.delete(this.url) : this.$api.post(this.url);
            method.then(() => this.following = !this.following);
        }
    }
};
</script>

<style lang="less"></style>
