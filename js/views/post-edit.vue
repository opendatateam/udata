<template>
<div>
    <form-layout icon="newspaper-o" :title="title" :save="save" :cancel="cancel" footer="true" :model="post">
        <post-form v-ref:form :post="post"></post-form>
        <button slot="right-actions"
            class="btn btn-primary"
            @click.prevent="saveAndContinue">
            {{ _('Save and continue') }}
        </button>
        <button v-if="!post.published" slot="right-actions"
            class="btn btn-primary"
            @click.prevent="publish">
            {{ _('Publish') }}
        </button>
    </form-layout>
</div>
</template>

<script>
import API from 'api';
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
        saveThen(callback) {
            const form = this.$refs.form;
            if (form.validate()) {
                this.post.update(form.serialize(), (response) => {
                    this.post.on_fetched(response);
                    if (callback) {
                        callback()
                    }
                }, form.on_error);
            }
        },
        save() {
            this.saveThen(() => {
                this.$go({name: 'post', params: {oid: this.post.id}});
            })
        },
        saveAndContinue() {
            this.saveThen()
        },
        publish() {
            this.saveThen(() => {
                API.posts.publish_post({post: this.post.id}, (response) => {
                    this.post.on_fetched(response);
                    this.$dispatch('notify', {
                        autoclose: true,
                        title: this._('Post published'),
                    });
                    this.$go({name: 'post', params: {oid: this.post.id}});
                }, this.$root.handleApiError);
            });
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
