<template>
<div>
    <form-layout icon="user" :title="_('Edit user')" :save="save" :cancel="cancel" footer="true" :model="user">
        <user-form v-ref:form :user="user"></user-form>
    </form-layout>
</div>
</template>

<script>
import UserForm from 'components/user/form.vue';
import User from 'models/user';
import FormLayout from 'components/form-layout.vue';

export default {
    data() {
        return {user: new User()};
    },
    components: {FormLayout, UserForm},
    methods: {
        save() {
            const form = this.$refs.form;
            if (form.validate()) {
                this.user.update(form.serialize(), form.on_error);
            }
        },
        on_success() {
            this.$dispatch('notify', {
                autoclose: true,
                title: this._('Changes saved'),
                details: this._('User has been updated.')
            });
            this.$go({name: 'user'});
        },
        cancel() {
            this.$go({name: 'user'});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.user.id) {
                this.$scrollTo(this.$el);
                this.user.fetch(this.$route.params.oid);
                this.user.$once('updated', () => {
                    this.updHandler = this.user.$once('updated', this.on_success);
                });
            }
        },
        deactivate() {
            if (this.updHandler) {
                this.updHandler.remove();
                this.updHandler = undefined;
            }
        }
    }
};
</script>
