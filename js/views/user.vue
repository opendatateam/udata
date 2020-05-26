<template>
<div>
    <layout :title="user.fullname || ''" :subtitle="_('User')" :page="user.page || ''" :actions="actions">
        <div class="row">
            <profile :user="user" class="col-xs-12 col-md-6"></profile>
        </div>

        <div class="row">
            <dataset-list class="col-xs-12" :datasets="datasets"></dataset-list>
        </div>

        <div class="row">
            <reuse-list class="col-xs-12" :reuses="reuses"></reuse-list>
        </div>

        <div class="row">
            <community-list class="col-xs-12" :communities="communities"></community-list>
        </div>

        <div class="row">
            <harvesters id="harvesters-widget" class="col-xs-12" :owner="user"></harvesters>
        </div>
    </layout>
</div>
</template>

<script>
import moment from 'moment';
import User from 'models/user';
import Reuses from 'models/reuses';
import Datasets from 'models/datasets';
import CommunityResources from 'models/communityresources';

import Chart from 'components/charts/widget.vue';
import CommunityList from 'components/dataset/communityresource/list.vue';
import DatasetList from 'components/dataset/list.vue';
import Harvesters from 'components/harvest/sources.vue';
import Layout from 'components/layout.vue';
import Profile from 'components/user/profile.vue';
import ReuseList from 'components/reuse/list.vue';


export default {
    name: 'user-view',
    data() {
        return {
            user: new User(),
            reuses: new Reuses({query: {sort: '-created', page_size: 10}, mask: ReuseList.MASK}),
            datasets: new Datasets({query: {sort: '-created', page_size: 10}, mask: DatasetList.MASK}),
            communities: new CommunityResources({query: {sort: '-created_at', page_size: 10}}),
            y: [{
                id: 'datasets',
                label: this._('Datasets')
            }, {
                id: 'reuses',
                label: this._('Reuses')
            }]
        };
    },
    components: {
        Chart,
        CommunityList,
        DatasetList,
        Harvesters,
        Layout,
        Profile,
        ReuseList,
    },
    computed: {
        actions() {
            const actions = [];
            if (this.can_edit) {
                actions.push({
                    label: this._('Edit'),
                    icon: 'edit',
                    method: this.edit
                }, {
                    label: this._('Delete'),
                    icon: 'trash',
                    method: this.confirm_delete,
                });
            }
            return actions;
        },
        can_edit() {
            return this.$root.me.is_admin || this.user.id == this.$root.me;
        },
    },
    watch: {
        'user.id': function(id) {
            if (id) {
                this.reuses.clear().fetch({owner: id});
                this.datasets.clear().fetch({owner: id});
                this.communities.clear().fetch({owner: id});
            } else {
                this.datasets.clear();
                this.reuses.clear();
                this.communities.clear();
            }
        }
    },
    route: {
        data() {
            if (this.$route.params.oid !== this.user.id) {
                this.user.fetch(this.$route.params.oid);
                this.$scrollTo(this.$el);
            }
        }
    },
    methods: {
        edit() {
            this.$go('/user/edit/' + this.user.id + '/');
        },
        confirm_delete() {
            this.$root.$modal(
                require('components/user/delete-user-modal.vue'),
                {user: this.user},
            );
        }
    }
};
</script>
