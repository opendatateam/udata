<style lang="less">
.identity {
    img {
        width: 25px;
        height: 25px;
    }
}
</style>

<template>
<a class="identity" @click="click">
    <img :src="avatar" :alt="name">
    {{name}}
</a>
</template>

<script>
export default {
    computed: {
        avatar() {
            return this.$data.avatar
                || this.$data.avatar_url
                || this.$data.logo
                || this.$data.logo_url;
        },
        name() {
            if (this.id === this.$root.me.id) {
                return this._('you');
            }
            return this.$data.fullname || this.$data.name;
        }
    },
    methods: {
        click() {
            this.$dispatch('identity:clicked', this);
        }
    }
};
</script>
