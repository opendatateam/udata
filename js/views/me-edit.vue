<template>
<div>
<form-layout icon="user" :title="_('Edit profile')" :save="save" :cancel="cancel" footer="true" :model="me">
    <user-form v-ref:form :user="me"></user-form>
</form-layout>
<div>
</template>

<script>
import UserForm from 'components/user/form.vue';
import me from 'models/me';
import FormLayout from 'components/form-layout.vue';

export default {
    name: 'me-edit',
    data() {
        return {me};
    },
    components: {FormLayout, UserForm},
    methods: {
        save() {
            const form = this.$refs.form;
            if (form.validate()) {
                this.me.update(form.serialize(), form.on_error);
            }
        },
        on_success() {
            this.$dispatch('notify', {
                autoclose: true,
                title: this._('Changes saved'),
                details: this._('Your profile has been updated.')
            });
            this.$go({name: 'me'});
        },
        cancel() {
            this.$go({name: 'me'});
        }
    },
    route: {
        data() {
            this.$scrollTo(this.$el);
            this.me.fetch();
            this.me.$once('updated', () => {
                this.updHandler = this.me.$once('updated', this.on_success);
            });
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
