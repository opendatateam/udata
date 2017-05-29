<template>
<div>
    <datatable :title="title" icon="comment"
        boxclass="discussions-widget"
        :fields="fields"
        :p="discussions"
        :empty="_('No discussion')">
    </datatable>
</div>
</template>

<script>
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'discussions-list',
    components: {Datatable},
    MASK: ['id', 'title', 'created', 'closed', 'class', 'subject'],
    data() {
        return {
            fields: [{
                label: this._('Title'),
                key: 'title',
                type: 'text',
                ellipsis: true
            }, {
                label: this._('Created on'),
                key: 'created',
                type: 'datetime',
                width: 200
            }, {
                label: this._('Closed on'),
                key: 'closed',
                type: 'datetime',
                width: 200
            }]
        };
    },
    events: {
        'datatable:item:click': function(discussion) {
            const prefix = discussion.subject.class.toLowerCase();
            const route = `${prefix}-discussion`;
            this.$go({name: route, params: {
                oid: discussion.subject.id,
                discussion_id: discussion.id
            }});
        }
    },
    props: {
        discussions: null,
        title: {
            type: String,
            default() {return this._('Discussions')},
        }
    }
};
</script>
