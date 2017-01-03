<template>
<form-layout icon="book" :title="title" :save="save" :cancel="cancel" footer="true" :model="topic">
    <topic-form v-ref:form :topic="topic"></topic-form>
</form-layout>
</template>

<script>
import TopicForm from 'components/topic/form.vue';
import Topic from 'models/topic';
import FormLayout from 'components/form-layout.vue';

export default {
    data() {
        return {
            topic: new Topic(),
        };
    },
    components: {FormLayout, TopicForm},
    computed: {
        title() {
            if (this.topic.name) {
                return this._('Edit topic "{name}"', {
                    name: this.topic.name
                });
            }
        }
    },
    methods: {
        save() {
            const form = this.$refs.form;
            if (form.validate()) {
                this.topic.update(form.serialize(), (response) => {
                    this.topic.on_fetched(response);
                    this.$go({name: 'topic', params: {oid: this.topic.id}});
                }, form.on_error);
            }
        },
        cancel() {
            this.$go({name: 'topic', params: {oid: this.topic.id}});
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.topic.id) {
                this.topic.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    }
};
</script>
