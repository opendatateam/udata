<template>
<layout :title="_('Search')">
    <div class="row">
        <datasets class="col-xs-12" :datasets="datasets" :title="datasetsTitle">
        </datasets>
    </div>
    <div class="row">
        <communities class="col-xs-12" :communities="communities" :title="communitiesTitle">
        </communities>
    </div>
    <div class="row">
        <reuses class="col-xs-12" :reuses="reuses" :title="reusesTitle">
        </reuses>
    </div>
    <div class="row">
        <issues class="col-xs-12" :issues="issues" :title="issuesTitle">
        </issues>
    </div>
    <div class="row">
        <discussions class="col-xs-12" :discussions="discussions" :title="discussionsTitle">
        </discussions>
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
        communities: require('components/communityresource/list.vue'),
        reuses: require('components/reuse/list.vue'),
        issues: require('components/issues/list.vue'),
        discussions: require('components/discussions/list.vue'),
        Layout
    },
    data() {
        return {
            datasetsTitle: '',
            datasets: new PageList({
                ns: 'me',
                fetch: 'my_org_datasets'
            }),
            communitiesTitle: '',
            communities: new PageList({
                ns: 'me',
                fetch: 'my_org_community_resources'
            }),
            reusesTitle: '',
            reuses: new PageList({
                ns: 'me',
                fetch: 'my_org_reuses'
            }),
            issuesTitle: '',
            issues: new PageList({
                ns: 'me',
                fetch: 'my_org_issues',
            }),
            discussionsTitle: '',
            discussions: new PageList({
                ns: 'me',
                fetch: 'my_org_discussions'
            }),
        };
    },
    route: {
        data() {
            const terms = this.$route.query.terms;
            this.datasetsTitle = this._(`Datasets related to your data about "${terms}"`);
            this.datasets.fetch({'q': terms});
            this.communitiesTitle = this._(`Community resources related to your data about "${terms}"`);
            this.communities.fetch({'q': terms});
            this.reusesTitle = this._(`Reuses related to your data about "${terms}"`);
            this.reuses.fetch({'q': terms});
            this.issuesTitle = this._(`Issues related to your data about "${terms}"`);
            this.issues.fetch({'q': terms});
            this.discussionsTitle = this._(`Discussions related to your data about "${terms}"`);
            this.discussions.fetch({'q': terms});
        }
    },
};
</script>
