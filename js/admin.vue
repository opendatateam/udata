<template>
<div>
    <!-- Placeholder for non-routable modals -->
    <div v-el:modal></div>
    <app-header class="main-header"></app-header>
    <sidebar></sidebar>
    <router-view></router-view>
</div>
</template>

<script>
import Vue from 'vue';

import config from 'config';
import me from 'models/me';
import site from 'models/site';

import AppHeader from 'components/header.vue';
import Sidebar from 'components/sidebar.vue';


export default {
    name: 'admin',
    data() {
        return {
            toggled: false,
            notifications: [],
            site, me, config,
        };
    },
    components: {AppHeader, Sidebar},
    events: {
        'navigation:toggled': function() {
            document.body.classList.toggle('sidebar-collapse');
            document.body.classList.toggle('sidebar-open');
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
        // Display an error identifier un uncaught error
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
        /**
         * Insert a modal Vue in the application.
         * @param  {Object} options     The modal component definition (options passed to Vue.extend())
         * @param  {Object} data        Data to assign to modal properties
         * @return {Vue}                The child instanciated vm
         */
        $modal(options, propsData) {
            const constructor = Vue.extend(options);
            const el = document.createElement('div');
            this.$els.modal.appendChild(el);
            const modal = new constructor({el, parent: this, propsData});
            modal.$on('modal:closed', modal.$destroy);
            return modal;
        }
    }
};
</script>
