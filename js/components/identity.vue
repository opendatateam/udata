<style lang="less">
.identity {
    img {
        width: 25px;
        height: 25px;
    }
}
</style>

<template>
<a class="identity" v-on="click: click">
    <img v-attr="src: avatar" alt="{{ name }}">
    {{name}}
</a>
</template>

<script>
'use strict';

module.exports = {
    replace: true,
    data: function() {
        return {};
    },
    computed: {
        avatar: function() {
            return this.$data.avatar
                || this.$data.avatar_url
                || this.$data.logo
                || this.$data.logo_url;
        },
        name: function() {
            if (this.id === this.$root.me.id) {
                return this._('you');
            }
            return this.$data.fullname || this.$data.name;
        }
    },
    methods: {
        click: function() {
            this.$dispatch('identity:clicked', this);
        }
    }
};
</script>
