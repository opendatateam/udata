<template>
<form-layout icon="building" :title="title" :save="save" :cancel="cancel" footer="true" :model="org">
    <org-form v-ref:form :organization="org"></org-form>
</form-layout>
</template>
<script>
import FormLayout from 'components/form-layout.vue';
import OrgForm from 'components/organization/form.vue';
import Organization from 'models/organization';

export default {
    data: function() {
        return {
            org: new Organization(),
        };
    },
    components: {FormLayout, OrgForm},
    computed: {
        title() {
            if (this.org.id) {
                return this._('Edit organization "{name}"', {
                    name: this.org.name
                });
            }
        }
    },
    methods: {
        save() {
            let form = this.$refs.form;
            if (form.validate()) {
                this.org.update(form.serialize(), (response) => {
                    this.org.on_fetched(response);
                    this.$go({name: 'organization', params: {oid: this.org.id}});
                }, form.on_error);
            }
        },
        cancel() {
            this.$go({name: 'organization', params: {oid: this.org.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.org.id) {
                this.org.fetch(this.$route.params.oid);
            }
        }
    }
};
</script>
