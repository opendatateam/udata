<template>
<layout :title="title">
    <div class="row">
        <datasets class="col-xs-12" :datasets="datasets"></datasets>
    </div>
    <div class="row">
        <communities class="col-xs-12" :communities="communities"></communities>
    </div>
    <div class="row">
        <reuses class="col-xs-12" :reuses="reuses"></reuses>
    </div>
    <div class="row">
        <issues class="col-xs-12" :issues="issues"></issues>
    </div>
    <div class="row">
        <discussions class="col-xs-12" :discussions="discussions"></discussions>
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
            let title = this._('Search');
            if (this.subtitle) {
                title = `${title} (${this.subtitle})`;
            }
            return title;
        }
    },
    data() {
        return {
            subtitle: undefined,
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
            this.subtitle = this._('related to your data about "{terms}"', {terms: terms});
            this.datasets.fetch({'q': terms});
            this.communities.fetch({'q': terms});
            this.reuses.fetch({'q': terms});
            this.issues.fetch({'q': terms});
            this.discussions.fetch({'q': terms});
        }
    },
};
</script>
