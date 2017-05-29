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
                this.dataset.update(form.serialize(), (response) => {
                    this.dataset.on_fetched(response);
                    this.$go({name: 'dataset', params: {oid: this.dataset.id}});
                }, form.on_error);
            }
        },
        cancel() {
            this.$go({name: 'dataset', params: {oid: this.dataset.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.dataset.id) {
                this.dataset.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    }
};
</script>
