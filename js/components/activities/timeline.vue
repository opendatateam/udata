<template>
<ul class="timeline">
    <li v-repeat="activity in enhancedActivities">
        <i class="{{ activity.icon }} timeline-icon"></i>
        <div class="timeline-item">
            <span class="time"><i class="fa fa-clock-o"></i> {{ activity.created_at | timeago }}</span>
            <div class="timeline-header">
                <h5>
                    <a v-if="activity.organization" href="{{ activity.url }}">{{ activity.organization.name }}</a>
                    <a v-if="!activity.organization" href="{{ activity.url }}">{{activity.actor.first_name}} {{activity.actor.last_name}}</a>
                    {{ activity.label }}
                    <a href="{{ activity.related_to_url }}">{{ activity.related_to }}</a>
                </h5>
            </div>
            <div class="timeline-body">
                <dataset-card v-if="activity.related_to_kind === 'Dataset'" datasetid="{{ activity.related_to_id }}"></dataset-card>
                <organization-card v-if="activity.related_to_kind === 'Organization'" organizationid="{{ activity.related_to_id }}"></organization-card>
                <reuse-card v-if="activity.related_to_kind === 'Reuse'" reuseid="{{ activity.related_to_id }}"></reuse-card>
                <user-card v-if="activity.related_to_kind === 'User'" userid="{{ activity.related_to_id }}"></user-card>
            </div>
            <div class="timeline-footer"></div>
        </div>
    </li>
    <li><i v-on="click: more" v-el="more" class="fa fa-chevron-down timeline-icon timeline-icon-more"></i></li>
</ul>
</template>

<script>
import ActivityPage from 'models/activities';
import URLs from 'urls';

export default {
    el: '#activities',
    props: ['organizationId', 'userId'],
    components: {
        'dataset-card': require('components/dataset/card.vue'),
        'organization-card': require('components/organization/card.vue'),
        'reuse-card': require('components/reuse/card.vue'),
        'user-card': require('components/user/card.vue'),
    },
    data: function() {
        this.options = {
            organization: this.organizationId,
            user: this.userId,
        };
        return {
            activities: new ActivityPage({cumulative: true}).fetch(this.options),
            currentPage: 1
        };
    },
    computed: {
        enhancedActivities: function() {
            return this.activities.data ? this.activities.data.map((activity) => {
                if (activity.organization) {
                    activity['url'] = URLs.build('organizations.show', {org: activity.organization});
                } else {
                    activity['url'] = URLs.build('users.show', {user: activity.actor});
                }
                return activity;
            }) : [];
        }
    },
    methods: {
        more: function() {
            let moreElement = this.$$.more
            moreElement.classList.remove("fa-chevron-down");
            moreElement.classList.add("fa-spinner", "fa-spin");
            this.activities.nextPage(this.options);
            this.activities.$on('updated', (activities) => {
                moreElement.classList.remove("fa-spinner", "fa-spin");
                moreElement.classList.add("fa-chevron-down");
            });
        }
    }
};
</script>
