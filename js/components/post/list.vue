<template>
    <datatable :title="_('Posts') " icon="newspaper-o"
        boxclass="posts-widget"
        :fields="fields"
        :p="posts"
        :empty="_('No post')">
        <footer slot="footer">
            <button type="button" class="btn btn-primary btn-flat btn-sm"
                v-link.literal="/post/new/">
                <span class="fa fa-fw fa-plus"></span>
                <span v-i18n="New"></span>
            </button>
        </footer>
    </datatable>
</template>


<script>
import Datatable from 'components/datatable/widget.vue';

export default {
    name: 'posts-widget',
    MASK: ['id', 'name', 'created_at', 'last_modified', 'private'],
    props: ['posts'],
    components: {Datatable},
    data() {
        return {
            fields: [{
                label: this._('Name'),
                key: 'name',
                sort: 'name',
                type: 'text'
            },{
                label: this._('Creation'),
                key: 'created_at',
                sort: 'created',
                align: 'left',
                type: 'timeago',
                width: 120
            }, {
                label: this._('Modification'),
                key: 'last_modified',
                sort: 'last_modified',
                align: 'left',
                type: 'timeago',
                width: 120
            }, {
                label: this._('Access'),
                key: 'private',
                sort: 'private',
                align: 'left',
                type: 'visibility',
                width: 120
            }]
        };
    },
    events: {
        'datatable:item:click': function(post) {
            this.$go({name: 'post', params: {oid: post.id}});
        }
    }
};
</script>
