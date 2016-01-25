<template>
<layout :title="title">
    <div class="row" v-if="datasets.loading || datasets.has_data">
        <datasets class="col-xs-12" :datasets="datasets"></datasets>
    </div>
    <div class="row" v-if="communities.loading || communities.has_data">
        <communities class="col-xs-12" :communities="communities"></communities>
    </div>
    <div class="row" v-if="reuses.loading || reuses.has_data">
        <reuses class="col-xs-12" :reuses="reuses"></reuses>
    </div>
    <div class="row" v-if="issues.loading || issues.has_data">
        <issues class="col-xs-12" :issues="issues"></issues>
    </div>
    <div class="row" v-if="discussions.loading || discussions.has_data">
        <discussions class="col-xs-12" :discussions="discussions"></discussions>
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

export default {
    name: 'SearchView',
    components: {
        datasets: require('components/dataset/list.vue'),
        communities: require('components/dataset/communityresource/list.vue'),
        reuses: require('components/reuse/list.vue'),
        issues: require('components/issues/list.vue'),
        discussions: require('components/discussions/list.vue'),
        Layout
    },
    computed: {
        title() {
            return [
                this._('Search in your data'),
                this.$route.query.terms
            ].join(': ');
        },
        no_results() {
            const collections = [this.datasets, this.communities, this.reuses, this.issues, this.discussions];
            return !collections.some(function(collection) {
                return collection.loading || collection.has_data;
            });
        }
    },
    data() {
        return {
            datasets: new PageList({
                ns: 'me',
                fetch: 'my_org_datasets'
            }),
            communities: new PageList({
                ns: 'me',
                fetch: 'my_org_community_resources'
            }),
            reuses: new PageList({
                ns: 'me',
                fetch: 'my_org_reuses'
            }),
            issues: new PageList({
                ns: 'me',
                fetch: 'my_org_issues',
            }),
            discussions: new PageList({
                ns: 'me',
                fetch: 'my_org_discussions'
            }),
        };
    },
    route: {
        data() {
            const terms = this.$route.query.terms;
            this.datasets.fetch({'q': terms});
            this.communities.fetch({'q': terms});
            this.reuses.fetch({'q': terms});
            this.issues.fetch({'q': terms});
            this.discussions.fetch({'q': terms});
        }
    },
};
</script>
