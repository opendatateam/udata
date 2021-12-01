<template>
<li class="dropdown notifications-menu">
    <a href="#" class="dropdown-toggle" data-toggle="dropdown">
        <i class="fa fa-envelope-o"></i>
        <span v-if="notifications.length > 0"
            class="label label-warning">{{notifications.length}}</span>
    </a>
    <ul class="dropdown-menu">
        <li class="header text-center" v-i18n="Notifications"></li>
        <li>
            <ul class="menu">
                <li v-for="notification in notifications">
                    <component :is="notification.type"
                        :details="notification.details"></component>
                </li>
            </ul>
        </li>
    </ul>
</li>
</template>

<script>
import API from 'api';

const INITIAL_FETCH = 5 * 1000;
const POLL_INTERVAL = 30 * 1000;

export default {
    name: 'notification-menu',
    data() {
        return {
            notifications: []
        };
    },
    // Components name matters (beware of the low dash)
    components: {
        'discussion': require('components/notifications/discussion.vue'),
        'membership_request': require('components/notifications/membership_request.vue'),
        'transfer_request': require('components/notifications/transfer.vue'),
        'validate_harvester': require('components/notifications/validate-harvester.vue'),
    },
    created() {
        // Trigger an initial fetch (don't wait for poll interval)
        setTimeout(this.fetch.bind(this), INITIAL_FETCH);
        // Start polling
        setInterval(this.fetch.bind(this), POLL_INTERVAL);
    },
    methods: {
        fetch() {
            API.notifications.get_notifications({}, (response) => {
                this.notifications = response.obj;
            });
        }
    }
};
</script>
