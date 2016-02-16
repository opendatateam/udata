<template>
<vform v-ref:form :fields="fields" :model="topic"></vform>
</template>

<script>
import Topic from 'models/topic';

export default {
    props: {
        topic: {
            type: Topic,
            default: function() {
                return new Topic();
            }
        }
    },
    data: function() {
        return {
            fields: [{
                    id: 'name',
                    label: this._('Name')
                }, {
                    id: 'description',
                    label: this._('Description')
                }, {
                    id: 'tags',
                    label: this._('Tags'),
                    widget: 'tag-completer'
                }, {
                    id: 'featured',
                    label: this._('Featured')
                }]
        };
    },
    components: {
        vform: require('components/form/vertical-form.vue')
    }
};
</script>
