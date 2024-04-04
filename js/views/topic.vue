<template>
<div>
<layout :title="topic.name || ''" :subtitle="_('Topic')" :page="topic.page || ''"
    :actions="actions">
    <div class="row">
        <topic-details :topic="topic" class="col-xs-12"></topic-details>
    </div>
    <div class="row">
        <datasets-list editable :datasets="topic.datasets" class="col-xs-12 col-md-6"></datasets-list>
        <reuses-list editable :reuses="topic.reuses" class="col-xs-12 col-md-6"></reuses-list>
    </div>
</layout>
</div>
</template>

<script>
import moment from 'moment';

import Topic from 'models/topic';
import Dataset from 'models/dataset';
import Reuse from 'models/reuse';
import mask from 'models/mask';

import Layout from 'components/layout.vue';
import TopicDetails from 'components/topic/details.vue';
import DeleteModal from 'components/topic/delete-modal.vue';
import DatasetsList from 'components/dataset/card-list.vue';
import ReusesList from 'components/reuse/card-list.vue';

const MASK = `datasets{${mask(DatasetsList.MASK)}},reuses{${mask(ReusesList.MASK)}},*`;

export default {
    name: 'TopicView',
    data() {
        return {
            topic: new Topic({mask: MASK}),
            actions: [{
                label: this._('Edit'),
                icon: 'edit',
                method: this.edit
            }, {
                label: this._('Delete'),
                icon: 'trash',
                method: this.confirm_delete
            }],
        };
    },
    components: {Layout, TopicDetails, DatasetsList, ReusesList},
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
        },
        confirm_delete() {
            this.$root.$modal(DeleteModal, {topic: this.topic});
        },
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
