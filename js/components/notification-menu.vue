<style lang="less">

</style>

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
                <li v-repeat="notifications">
                    <component is="{{type}}"></component>
                </li>
            </ul>
        </li>
    </ul>
</li>
</template>

<script>
'use strict';

var API = require('api'),
    INITIAL_FETCH = 5 * 1000,
    POLL_INTERVAL = 30 * 1000;

module.exports = {
    replace: true,
    data: function() {
        return {
            notifications: []
        };
    },
    components: {
        'issue': require('components/notifications/issue.vue'),
        'membership_request': require('components/notifications/membership_request.vue'),
        'transfer_request': require('components/notifications/transfer.vue')
    },
    created: function() {
        // Trigger an initial fetch (don't wait for poll interval)
        setTimeout(this.fetch.bind(this), INITIAL_FETCH);
        // Start polling
        setInterval(this.fetch.bind(this), POLL_INTERVAL);
    },
    methods: {
        fetch: function() {
            API.me.notifications({}, function(response) {
                this.notifications = response.obj;
            }.bind(this));
        }
    }
};
</script>
