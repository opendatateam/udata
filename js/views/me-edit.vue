<template>
<form-layout icon="user" :title="_('Edit profile')" :save="save" :cancel="cancel" footer="true" :model="me">
    <user-form v-ref:form :user="me"></user-form>
</form-layout>
</template>

<script>
import UserForm from 'components/user/form.vue';
import me from 'models/me';
import FormLayout from 'components/form-layout.vue';

export default {
    data: function() {
        return {me};
    },
    components: {FormLayout, UserForm},
    methods: {
        save() {
            let form = this.$refs.form;
            if (form.validate()) {
                this.me.update(form.serialize(), (response) => {
                    this.me.on_fetched(response);
                    this.$go({name: 'me'});
                }, form.on_error);
            }
        },
        cancel() {
            this.$go({name: 'me'});
        }
    },
    route: {
        data() {
            this.me.fetch();
            this.$scrollTo(this.$el);
        }
    }
};
</script>
