<template>
<div class="issues-list">
    <div class="modal-body">
        <div class="tab-pane fade in active" v-if="loading && !issues.length">
            <div class="text-center spinner-container">
                <i class="fa fa-2x fa-refresh fa-spin"></i>
            </div>
        </div>
        <div class="issue" v-for="issue in issues" @click="$dispatch('issue:selected', issue)">
            <div class="pull-left">
                <avatar :user="issue.user"></avatar>
            </div>
            <div class="media-body">
                <h4 class="media-heading text-left">{{issue.title}}</h4>
                <i>{{ issue.created|dt }}</i>
            </div>
        </div>
        <p v-if="!loading && !issues.length" class="text-center">{{ _('No issue.') }}</p>
        <p v-if="!loading && !issues.length" class="text-center">{{ _('Click on new issue if you want to emit a new one.') }}</p>
    </div>
    <footer class="modal-footer text-center">
        <button class="btn btn-primary" @click="$dispatch('new')">
            <span class="fa fa-plus"></span>
            {{ _('New issue') }}
        </button>
        <button type="button" class="btn btn-default" @click="$dispatch('close')">
            <span class="fa fa-times"></span>
            {{ _('Close') }}
        </button>
    </footer>
</div>
</template>
<script>
import Avatar from 'components/avatar.vue';

export default {
    components: {Avatar},
    props: {
        subject: {type: Object, required: true},
    },
    data() {
        return {
            loading: true,
            issues: [],
        };
    },
    ready() {
        this.$api
            .get('issues/', {for: this.subject.id})
            .then(response => {
                this.issues = response.data;
                this.loading = false;
            });
    }
};
</script>

<style lang="less">
@import '~bootstrap/less/variables.less';
@import '~bootstrap/less/media.less';

.issues-list {
    .issue {
        .media();
        background-color: @gray-lighter;
        cursor: pointer;

        .media-body {
            padding: 5px;
        }

        &:first-child {
            margin-top: 0;
        }
    }
}

</style>
