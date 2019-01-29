<template>
<div>
<form-layout icon="building" :title="title" :save="save" :cancel="cancel" footer="true" :model="org">
    <org-form v-ref:form :organization="org"></org-form>
</form-layout>
</div>
</template>

<script>
import FormLayout from 'components/form-layout.vue';
import OrgForm from 'components/organization/form.vue';
import Organization from 'models/organization';

export default {
    name: 'organization-edit',
    data() {
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
            const form = this.$refs.form;
            if (form.validate()) {
                this.org.update(form.serialize(), form.on_error);
            }
        },
        on_success() {
            this.$dispatch('notify', {
                autoclose: true,
                title: this._('Changes saved'),
                details: this._('Your organization has been updated.')
            });
            this.$go({name: 'organization', params: {oid: this.org.id}});
        },
        cancel() {
            this.$go({name: 'organization', params: {oid: this.org.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.org.id) {
                this.$scrollTo(this.$el);
                this.org.fetch(this.$route.params.oid);
                this.org.$once('updated', () => {
                    this.updHandler = this.org.$once('updated', this.on_success);
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
