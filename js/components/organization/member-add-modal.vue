<style lang="less">
.member-form {
    .form-group {
        margin-bottom: 0;
    }
}
</style>

<template>
<user-modal :user="user">
    <role-form class="member-form"
        :fields="fields" :model="member" :defs="defs">
    </role-form>
</user-modal>
</template>

<script>
import User from 'models/user';
import Vue from'vue';
import API from 'api';

export default {
    name: 'member-modal',
    props: {
        member: Object
    },
    data: function() {
        return {
            user: new User(),
            horizontal: true,
            fields: [{
                id: 'role',
                label: this._('Role'),
                widget: 'select-input'
            }],
            defs: API.definitions.Member
        };
    },
    components: {
        'user-modal': require('components/user/modal.vue'),
        'role-form': require('components/form/horizontal-form.vue')
    },
    ready: function() {
        this.user.fetch(this.member.user.id);
    }
};
</script>
