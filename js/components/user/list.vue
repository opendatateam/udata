<template>
    <datatable :title="title" icon="users"
        boxclass="users-widget"
        :fields="fields"
        :p="users"
        :empty="_('No user')">
    </datatable>
</template>

<script>
export default {
    name: 'users-widget',
    components: {
        datatable: require('components/datatable/widget.vue')
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
                key: 'since',
                sort: 'since',
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
            }, {
                label: this._('Roles'),
                key: 'roles',
                align: 'center',
                type: 'label',
                width: 95
            }]
        };
    },
    events: {
        'datatable:item:click': function(user) {
            this.$go('/user/' + user.id + '/');
        }
    },
    props: ['users']
};
</script>
