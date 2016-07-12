<template>
<vform v-ref:form :fields="fields" :model="topic"></vform>
</template>

<script>
import Topic from 'models/topic';
import Vform from 'components/form/vertical-form.vue';

export default {
    props: {
        topic: {
            type: Topic,
            default() {
                return new Topic();
            }
        }
    },
    data() {
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
    components: {Vform},
    methods: {
        serialize() {
            return this.$refs.form.serialize();
        },
        validate() {
            return this.$refs.form.validate();
        }
    }
};
</script>
