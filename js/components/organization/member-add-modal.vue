<style lang="less">
.member-form {
    .form-group {
        margin-bottom: 0;
    }
}
</style>

<template>
<user-modal user="{{user}}">
    <role-form class="member-form"
        fields="{{fields}}" model="{{member}}" defs="{{defs}}">
    </role-form>
</user-modal>
</template>

<script>
'use strict';

var User = require('models/user'),
    Vue = require('vue'),
    API = require('api');

module.exports = {
    name: 'member-modal',
    data: function() {
        return {
            user: new User(),
            horizontal: true,
            fields: [{
                id: 'role',
                label: this._('Role'),
                widget: 'select-input'
            }],
            member: {},
            defs: API.definitions.Member
        };
    },
    paramAttributes: ['member'],
    components: {
        'user-modal': require('components/user/modal.vue'),
        'role-form': require('components/form/horizontal-form.vue')
    },
    ready: function() {
        this.user.fetch(this.member.user.id);
        // this.member.$log();
    }
};
</script>
