<template>
<div>
<form-layout icon="cubes" :title="title" :save="save" :cancel="cancel" footer="true" :model="dataset">
    <dataset-form v-ref:form :dataset="dataset"></dataset-form>
</form-layout>
</div>
</template>

<script>
import DatasetForm from 'components/dataset/form.vue';
import Dataset from 'models/dataset';
import FormLayout from 'components/form-layout.vue';

export default {
    name: 'dataset-edit',
    data() {
        return {
            dataset: new Dataset(),
        };
    },
    components: {FormLayout, DatasetForm},
    computed: {
        title() {
            if (this.dataset.id) {
                return this._('Edit dataset "{title}"', {
                    title: this.dataset.title
                });
            }
        }
    },
    methods: {
        save() {
            const form = this.$refs.form;
            if (form.validate()) {
                this.dataset.update(form.serialize(), form.on_error);
            }
        },
        on_success() {
            this.$dispatch('notify', {
                autoclose: true,
                title: this._('Changes saved'),
                details: this._('Your dataset has been updated.')
            });
            this.$go({name: 'dataset', params: {oid: this.dataset.id}});
        },
        cancel() {
            this.$go({name: 'dataset', params: {oid: this.dataset.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.dataset.id) {
                this.$scrollTo(this.$el);
                this.dataset.fetch(this.$route.params.oid);
                this.dataset.$once('updated', () => {
                    this.updHandler = this.dataset.$once('updated', this.on_success);
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
