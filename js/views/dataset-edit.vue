<template>
<form-layout icon="cubes" :title="title" :save="save" :cancel="cancel" footer="true" :model="dataset">
    <dataset-form v-ref:form :dataset="dataset"></dataset-form>
</form-layout>
</template>

<script>
import Box from 'components/containers/box.vue';
import DatasetForm from 'components/dataset/form.vue';
import DatasetFull from 'models/dataset_full';
import FormLayout from 'components/form-layout.vue';

export default {
    data: function() {
        return {
            dataset: new DatasetFull(),
        };
    },
    components: {Box, FormLayout, DatasetForm},
    computed: {
        title() {
            return this._('Edit dataset {title}', {
                title: this.dataset.title || ''
            });
        }
    },
    methods: {
        save() {
            let form = this.$refs.form;
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
            }
        }
    }
};
</script>
