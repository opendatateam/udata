<template>
<div class="activity-timeline">
    <div v-if="activities.loading && !enhancedActivities" class="text-center"><span class="fa fa-4x fa-cog fa-spin"></span></div>
    <ul v-if="enhancedActivities" class="timeline">
        <li v-for="activity in enhancedActivities">
            <i :class="activity.icon" class="timeline-icon"></i>
            <div class="timeline-item">
                <span class="time" :title="activity.created_at"><i class="fa fa-clock-o"></i> {{ activity.created_at | timeago }}</span>
                <div class="timeline-header">
                    <h5>
                        <span v-if="activity.aggregatedFollowing">
                            <span v-for="(index, actor) in activity.aggregaterActors">
                                <a :href="actor.url">{{actor | displayName}}</a><span v-if="index < activity.aggregaterActors.length - 2">,</span>
                                <span v-if="index === activity.aggregaterActors.length - 2">{{ _('and') }}</span>
                            </span>
                            {{ activity.aggregatedLabel }}
                        </span>
                        <span v-if="!activity.aggregatedFollowing">
                            <a :href="actor(activity).url">{{ actor(activity) | displayName }}</a>
                            {{ activity.label }}
                        </span>
                        <a :href="activity.related_to_url">{{ activity.related_to }}</a>
                    </h5>
                </div>
                <div class="timeline-body">
                    <dataset-card v-if="activity.related_to_kind === 'Dataset'" :datasetid="activity.related_to_id"></dataset-card>
                    <organization-card v-if="activity.related_to_kind === 'Organization'" :orgid="activity.related_to_id"></organization-card>
                    <reuse-card v-if="activity.related_to_kind === 'Reuse'" :reuseid="activity.related_to_id"></reuse-card>
                    <user-card v-if="activity.related_to_kind === 'User'" :userid="activity.related_to_id"></user-card>
                </div>
            </div>
        </li>
        <li v-if="hasMore"><i @click="more" v-el:more class="fa fa-chevron-down timeline-icon timeline-icon-more"></i></li>
    </ul>
</div>
</template>

<script>
import moment from 'moment';
import ActivityPage from 'models/activities';
import URLs from 'urls';

function actor(activity) {
    return activity.organization || activity.actor;
}

export default {
    props: ['organizationId', 'userId'],
    components: {
        'dataset-card': require('components/dataset/card.vue'),
        'organization-card': require('components/organization/card.vue'),
        'reuse-card': require('components/reuse/card.vue'),
        'user-card': require('components/user/card.vue'),
    },
    data: function() {
        return {
            activities: new ActivityPage({cumulative: true})
        };
    },
    ready: function() {
        this.activities.fetch(this.options);
    },
    computed: {
        options: function() {
            return {
                organization: this.organizationId,
                user: this.userId,
            };
        },
        enhancedActivities: function() {
            let previousActivity = {};
            // Sort twice by created date to keep creations over updates
            // using the previousActivity accumulator.
            return this.activities.data ? this.activities.data.sort((a, b) => {
                return a.created_at > b.created_at;
            }).map((activity) => {
                // Add URLs to the organization or actor.
                if (activity.organization) {
                    activity.organization.url = URLs.build('organizations.show', {org: activity.organization});
                } else {
                    activity.actor.url = URLs.build('users.show', {user: activity.actor});
                }
                activity.aggregatedFollowing = false;
                activity.aggregaterActors = [];
                activity.aggregatedLabel = "";
                if (previousActivity
                    && previousActivity.related_to === activity.related_to) {
                    if (this.isADuplicate(activity, previousActivity)) {
                        return;
                    } else if (previousActivity.label === activity.label) {
                        // Aggregate followers.
                        if (activity.key === 'organization:followed') {
                            previousActivity.aggregatedFollowing = true;
                            previousActivity.aggregaterActors.push(activity.actor);
                            previousActivity.aggregatedLabel = this._("followed organization");
                            return;
                        } else if (this.updateOrgTheSameDay(activity, previousActivity)) {
                            return;
                        } else if (this.updateDatasetTheSameDay(activity, previousActivity)) {
                            return;
                        }
                    } else if (this.updateOrCreateTheSameDay(activity, previousActivity)) {
                        return;
                    }
                }

                previousActivity = activity;
                return activity;
            }).filter((activity) => {
                return !!activity;
            }).sort((a, b) => {
                return a.created_at < b.created_at;
            }) : [];
        },
        hasMore: function() {
            return this.activities.total > this.activities.page * this.activities.page_size;
        }
    },
    filters: {
        displayName: function(actor) {
            return actor.name || actor.fullname || (actor.first_name + ' ' + actor.last_name);
        }
    },
    methods: {
        actor,
        more: function() {
            let moreElement = this.$els.more;
            moreElement.classList.remove("fa-chevron-down");
            moreElement.classList.add("fa-spinner", "fa-spin");
            this.activities.nextPage(this.options);
            this.activities.$on('updated', (activities) => {
                moreElement.classList.remove("fa-spinner", "fa-spin");
                moreElement.classList.add("fa-chevron-down");
            });
        },
        withinSameDay: function(firstDate, secondDate) {
            return moment(firstDate).isSame(secondDate, 'day');
        },
        isADuplicate: function(activity, previousActivity) {
            return previousActivity.label === activity.label
                && actor(previousActivity).id === actor(activity).id;
        },
        updateOrgTheSameDay: function(activity, previousActivity) {
            return activity.key === 'organization:updated'
                && actor(previousActivity).id === actor(activity).id
                && this.withinSameDay(previousActivity.created_at, activity.created_at);
        },
        updateDatasetTheSameDay: function(activity, previousActivity) {
            return activity.key === 'dataset:updated'
                && actor(previousActivity).id === actor(activity).id
                && this.withinSameDay(previousActivity.created_at, activity.created_at);
        },
        updateOrCreateTheSameDay: function(activity, previousActivity) {
            return previousActivity.key
                && (previousActivity.key.endsWith(':created')
                    || previousActivity.key.endsWith(':updated'))
                && activity.key.endsWith(':updated')
                && this.withinSameDay(previousActivity.created_at, activity.created_at);
        }
    }
};
</script>
