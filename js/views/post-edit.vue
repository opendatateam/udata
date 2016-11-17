<template>
<form-layout icon="newspaper-o" :title="title" :save="save" :cancel="cancel" footer="true" :model="post">
    <post-form v-ref:form :post="post"></post-form>
</form-layout>
</template>

<script>
import PostForm from 'components/post/form.vue';
import Post from 'models/post';
import FormLayout from 'components/form-layout.vue';

export default {
    data() {
        return {
            post: new Post(),
        };
    },
    components: {FormLayout, PostForm},
    computed: {
        title() {
            if (this.post.name) {
                return this._('Edit post "{name}"', {
                    name: this.post.name
                });
            }
        }
    },
    methods: {
        save() {
            const form = this.$refs.form;
            if (form.validate()) {
                this.post.update(form.serialize(), (response) => {
                    this.post.on_fetched(response);
                    this.$go({name: 'post', params: {oid: this.post.id}});
                }, form.on_error);
            }
        },
        cancel() {
            this.$go({name: 'post', params: {oid: this.post.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.post.id) {
                this.post.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    }
};
</script>
