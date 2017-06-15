<template>
<div>
<vertical-form v-ref:form :fields="fields" :model="topic"></vertical-form>
</div>
</template>

<script>
import Topic from 'models/topic';
import VerticalForm from 'components/form/vertical-form.vue';

export default {
    name: 'topic-form',
    components: {VerticalForm},
    props: {
        topic: {type: Topic, default: () => new Topic()},
        hideNotifications: false
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
    methods: {
        serialize() {
            return this.$refs.form.serialize();
        },
        validate() {
            const isValid = this.$refs.form.validate();

            if (isValid & !this.hideNotifications) {
                this.$dispatch('notify', {
                    autoclose: true,
                    title: this._('Changes saved'),
                    details: this._('Your topic has been updated.')
                });
            }
            return isValid;
        }
    }
};
</script>
