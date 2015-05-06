<template>
    <datatable-widget title="{{ title }}" icon="users"
        boxclass="users-widget"
        fields="{{ fields }}"
        p="{{ users }}">
        <footer>
            <button type="button" class="btn btn-primary btn-sm"
                v-class="pull-right: users.pages > 1"
                v-route="/user/new/">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="New"></span>
            </button>
        </footer>
    </datatable-widget>
</template>

<script>
'use strict';

module.exports = {
    name: 'users-widget',
    components: {
        'datatable-widget': require('components/widgets/datatable.vue')
    },
    data: function() {
        return {
            title: this._('Users'),
            fields: [{
                key: 'avatar',
                type: 'avatar',
                width: 30
            },{
                label: this._('First name'),
                key: 'first_name',
                sort: 'first_name',
                type: 'text'
            }, {
                label: this._('Last name'),
                key: 'last_name',
                sort: 'last_name',
                type: 'text'
            }, {
                label: this._('Member since'),
                key: 'created_at',
                sort: 'created',
                align: 'left',
                type: 'since',
                width: 135
            }, {
                label: this._('Datasets'),
                key: 'metrics.datasets',
                sort: 'datasets',
                align: 'center',
                type: 'metric',
                width: 135
            }, {
                label: this._('Reuses'),
                key: 'metrics.reuses',
                sort: 'reuses',
                align: 'center',
                type: 'metric',
                width: 125
            }, {
                label: this._('Followers'),
                key: 'metrics.followers',
                sort: 'followers',
                align: 'center',
                type: 'metric',
                width: 95
            }]
        };
    },
    events: {
        'datatable:item:click': function(user) {
            this.$go('/user/' + user.id + '/');
        }
    },
    paramAttributes: ['users']
};
</script>
