<template>
    <datatable title="{{ title }}" icon="book"
        boxclass="topics-widget"
        fields="{{ fields }}"
        p="{{ topics }}"
        empty="{{ _('No topic') }}">
        <footer>
            <button type="button" class="btn btn-primary btn-flat btn-sm"
                v-route="/topic/new/">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="New"></span>
            </button>
        </footer>
    </datatable>
</template>


<script>
'use strict';

module.exports = {
    name: 'topics-widget',
    components: {
         'datatable': require('components/widgets/datatable.vue')
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
