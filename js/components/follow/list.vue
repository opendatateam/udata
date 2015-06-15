<template>
    <datatable title="{{ title }}" icon="users"
        boxclass="followers-widget"
        fields="{{ fields }}"
        p="{{ followers }}"
        empty="{{ _('No follower') }}">
    </datatable>
</template>

<script>
'use strict';

module.exports = {
    name: 'followers-widget',
    components: {
        'datatable': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Followers'),
            fields: [{
                key: 'follower.avatar',
                type: 'avatar',
                width: 30
            }, {
                label: this._('First name'),
                key: 'follower.first_name',
                type: 'text'
            }, {
                label: this._('Last name'),
                key: 'follower.last_name',
                type: 'text'
            }, {
                label: this._('Since'),
                key: 'since',
                type: 'datetime'
            }]
        };
    },
    events: {
        'datatable:item:click': function(item) {
            this.$go('/user/' + item.follower.id + '/');
        }
    },
    props: ['followers']
};
</script>
