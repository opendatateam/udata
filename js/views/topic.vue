<template>
    <div class="row">
        <topic-details :topic="topic" class="col-xs-12"></topic-details>
    </div>
    <div class="row">
        <datasets-list :datasets="topic.datasets" class="col-xs-12 col-md-6"></datasets-list>
        <reuses-list :reuses="topic.reuses" class="col-xs-12 col-md-6"></reuses-list>
    </div>
</template>

<script>
import moment from 'moment';
import Topic from 'models/topic';

export default {
    name: 'TopicView',
    data: function() {
        return {
            topic_id: null,
            topic: new Topic(),
            meta: {
                title: null,
                subtitle: this._('Topic')
            }
        };
    },
    components: {
        'topic-details': require('components/topic/details.vue'),
        'datasets-list': require('components/dataset/card-list.vue'),
        'reuses-list': require('components/reuse/card-list.vue')
    },
    events: {
        'dataset-card-list:submit': function(ids) {
            this.topic.datasets = ids;
            this.topic.save();
        },
        'reuse-card-list:submit': function(ids) {
            this.topic.reuses = ids;
            this.topic.save();
        }
    },
    watch: {
        topic_id: function(id) {
            if (id) {
                this.topic.fetch(id);
            }
        },
        'topic.name': function(name) {
            if (name) {
                this.meta.title = name;
                this.$dispatch('meta:updated', this.meta);
            }
        }
    }
};
</script>
