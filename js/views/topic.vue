<template>
<layout :title="topic.name || ''" :subtitle="_('Topic')" :page="topic.page || ''"
    :actions="actions">
    <div class="row">
        <topic-details :topic="topic" class="col-xs-12"></topic-details>
    </div>
    <div class="row">
        <datasets-list :datasets="topic.datasets" class="col-xs-12 col-md-6"></datasets-list>
        <reuses-list :reuses="topic.reuses" class="col-xs-12 col-md-6"></reuses-list>
    </div>
</layout>
</template>

<script>
import moment from 'moment';
import Topic from 'models/topic';
import Layout from 'components/layout.vue';

export default {
    name: 'TopicView',
    data() {
        return {
            topic: new Topic(),
            actions: [{
                label: this._('Edit'),
                icon: 'edit',
                method: this.edit
            }],
        };
    },
    components: {
        'topic-details': require('components/topic/details.vue'),
        'datasets-list': require('components/dataset/card-list.vue'),
        'reuses-list': require('components/reuse/card-list.vue'),
        Layout
    },
    events: {
        'dataset-card-list:submit': function(ids) {
            this.topic.datasets = ids;
            this.topic.save();
            return true;
        },
        'reuse-card-list:submit': function(ids) {
            this.topic.reuses = ids;
            this.topic.save();
            return true;
        }
    },
    methods: {
        edit() {
            this.$go({name: 'topic-edit', params: {oid: this.topic.id}});
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
