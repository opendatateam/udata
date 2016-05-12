<template>
    <datatable :title="_('Topics')" icon="book"
        boxclass="topics-widget"
        :fields="fields"
        :p="topics"
        :empty="_('No topic')">
        <footer slot="footer">
            <button type="button" class="btn btn-primary btn-flat btn-sm"
                v-link.literal="/topic/new/">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="New"></span>
            </button>
        </footer>
    </datatable>
</template>


<script>
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'topics-widget',
    MASK: ['id', 'name'],
    components: {Datatable},
    props: ['topics'],
    data() {
        return {
            fields: [{
                label: this._('Name'),
                key: 'name',
                sort: 'name',
                type: 'text'
            }]
        };
    },
    events: {
        'datatable:item:click': function(topic) {
            this.$go({name: 'topic', params: {oid: topic.id}});
        }
    }
};
</script>
