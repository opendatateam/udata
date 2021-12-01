<template>
<layout :title="_('Search in your data: {q}', {q: $route.query.q})">
    <div class="row" v-if="datasets.loading || datasets.has_data">
        <datasets-list class="col-xs-12" :datasets="datasets"></datasets-list>
    </div>
    <div class="row" v-if="communities.loading || communities.has_data">
        <community-list class="col-xs-12" :communities="communities"></community-list>
    </div>
    <div class="row" v-if="reuses.loading || reuses.has_data">
        <reuses-list class="col-xs-12" :reuses="reuses"></reuses-list>
    </div>
    <div class="row" v-if="discussions.loading || discussions.has_data">
        <discussion-list class="col-xs-12" :discussions="discussions"></discussion-list>
    </div>
    <div class="row" v-if="no_results">
        <div class="col-xs-12 text-center">
            <p class="lead">{{_('No result found')}}</p>
        </div>
    </div>
</layout>
</template>

<script>
import {PageList} from 'models/base';
import Layout from 'components/layout.vue';
import DatasetList from 'components/dataset/list.vue';
import ReuseList from 'components/reuse/list.vue';
import DiscussionList from 'components/discussions/list.vue';
import CommunityList from 'components/dataset/communityresource/list.vue';

export default {
    name: 'SearchView',
    components: {
        CommunityList,
        DiscussionList,
        DatasetList,
        ReuseList,
        Layout
    },
    computed: {
        no_results() {
            const collections = [this.datasets, this.communities, this.reuses, this.discussions];
            return !collections.some(function(collection) {
                return collection.loading || collection.has_data;
            });
        }
    },
    data() {
        return {
            datasets: new PageList({
                ns: 'me',
                fetch: 'my_org_datasets',
                mask: DatasetList.MASK
            }),
            communities: new PageList({
                ns: 'me',
                fetch: 'my_org_community_resources',
                mask: CommunityList.MASK
            }),
            reuses: new PageList({
                ns: 'me',
                fetch: 'my_org_reuses',
                mask: ReuseList.MASK
            }),
            discussions: new PageList({
                ns: 'me',
                fetch: 'my_org_discussions',
                mask: DiscussionList.MASK
            }),
        };
    },
    route: {
        data() {
            const terms = this.$route.query.q;
            this.datasets.fetch({'q': terms});
            this.communities.fetch({'q': terms});
            this.reuses.fetch({'q': terms});
            this.discussions.fetch({'q': terms});
            this.$scrollTo(this.$el);
        }
    },
};
</script>
