<template>
<div>
    <!-- Placeholder for non-routable modals -->
    <div v-el:modal></div>
    <app-header></app-header>
    <sidebar></sidebar>
    <router-view></router-view>
</div>
</template>

<script>
import config from 'config';
import me from 'models/me';
import site from 'models/site';

import AppHeader from 'components/header.vue';
import Sidebar from 'components/sidebar.vue';
import ModalMixin from 'mixins/modal';


export default {
    name: 'admin',
    mixins: [ModalMixin],
    data() {
        return {
            toggled: true,
            notifications: [],
            site, me, config,
            readOnlyEnabled: config.read_only_enabled,
        };
    },
    components: {AppHeader, Sidebar},
    events: {
        'navigation:toggled': function() {
            document.body.classList.toggle('sidebar-collapse');
            document.body.classList.toggle('sidebar-open');
            this.toggled = !this.toggled;
        },
        notify: function(notification) {
            this.notifications.push(notification);
        },
        'notify:close': function(notification) {
            const index = this.notifications.indexOf(notification);
            this.notifications.splice(index, 1);
        }
    },
    ready() {
        // Displays a toast if read only mode is enabled
        if (this.readOnlyEnabled) {
            this.notifications.push({
                type: 'error',
                icon: 'exclamation-triangle',
                title: this._('Attention'),
                details: this._('Due to security reasons, the creation of new content is currently disabled.'),
            });
        }
        // Displays an error identifier on uncaught error
        document.addEventListener('ravenSuccess', (e) => {
            this.notifications.push({
                type: 'error',
                icon: 'exclamation-triangle',
                title: this._('An error occured'),
                details: this._('The error identifier is {id}', {id: e.data.event_id}),
            });
        });
    },
    methods: {
        handleApiError(response) {
            const notif = {type: 'error', icon: 'exclamation-circle'};
            if (response.status === 403) {
                notif.title = this._('Operation not permitted');
                notif.details = this._('You are not allowed to perform this operation');
                notif.icon = 'ban'
            } else {
                notif.title = this._('An error occured');
                const messages = [];

                if ('data' in response) {
                    let data = {};
                    try {
                        data = JSON.parse(response.data);
                    } catch (e) {
                        console.warn('Parsing error:', e);
                        // TODO: Optional Sentry handling
                    }

                    if ('errors' in data) {
                        messages.push(this._('Invalid API request:'));
                        Object.entries(data.errors).forEach(([field, errs]) => {
                            messages.push(`<strong>${field}</strong>: ${errs.join(', ')}`);
                        });
                    } else if ('message' in data) {
                        messages.push(data.message);
                    }
                }

                if (!messages.length) {
                    messages.push(this._('An unkown error occured'));
                }

                if (response.headers && 'X-Sentry-ID' in response.headers) {
                    messages.push(
                        this._('The error identifier is {id}', {id: response.headers['X-Sentry-ID']})
                    );
                }

                notif.details = messages.join('\n');
            }
            this.notifications.push(notif);
        }
    }
};
</script>
