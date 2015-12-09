<template>
    <datatable :title="title" icon="book"
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
export default {
    name: 'topics-widget',
    components: {
         datatable: require('components/datatable/widget.vue')
    },
    data: function() {
        return {
            title: this._('Topics'),
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
            this.$go('/topic/' + topic.id + '/');
        }
    },
    props: ['topics']
};
</script>
