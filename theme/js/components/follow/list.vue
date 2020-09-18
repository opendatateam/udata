<template>
<div>
    <datatable :title="title" icon="users"
        boxclass="followers-widget"
        :fields="fields"
        :p="followers"
        :empty="_('No follower')">
    </datatable>
</div>
</template>

<script>
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'followers-list',
    components: {Datatable},
    props: ['followers'],
    data() {
        return {
            title: this._('Followers'),
            fields: [{
                key: 'follower',
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
            this.$go(`/user/${item.follower.id}/`);
        }
    },
};
</script>
