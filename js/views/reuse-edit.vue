<template>
<form-layout icon="retweet" :title="title" :save="save" :cancel="cancel" footer="true" :model="reuse">
    <reuse-form v-ref:form :reuse="reuse"></reuse-form>
</form-layout>
</template>

<script>
import ReuseForm from 'components/reuse/form.vue';
import Reuse from 'models/reuse';
import FormLayout from 'components/form-layout.vue';

export default {
    data: function() {
        return {
            reuse: new Reuse(),
        };
    },
    components: {FormLayout, ReuseForm},
    computed: {
        title() {
            if (this.reuse.id) {
                return this._('Edit reuse "{title}"', {
                    title: this.reuse.title
                });
            }
        }
    },
    methods: {
        save() {
            let form = this.$refs.form;
            if (form.validate()) {
                this.reuse.update(form.serialize(), (response) => {
                    this.reuse.on_fetched(response);
                    this.$go({name: 'reuse', params: {oid: this.reuse.id}});
                }, form.on_error);
            }
        },
        cancel() {
            this.$go({name: 'reuse', params: {oid: this.reuse.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.reuse.id) {
                this.reuse.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    }
};
</script>
