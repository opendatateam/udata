<style lang="less">
// Fix slimscroll overflow
.main-sidebar:hover {
    .slimScrollDiv {
        overflow: visible!important;
        > .sidebar {
            overflow: visible!important;
        }
    }

}
</style>

<template>
    <!-- Placeholder for non-routable modals -->
    <div v-el:modal></div>
    <app-header class="main-header"></app-header>
    <sidebar class="main-sidebar"></sidebar>
    <router-view></router-view>
</template>

<script>
import $ from 'jquery';
import Vue from 'vue';
import me from 'models/me';
import site from 'models/site';
import 'jquery-slimscroll';

export default {
    name: 'App',
    data: function() {
        return {
            me: me,
            site: site,
            config: require('config'),
            toggled: false,
            notifications: []
        };
    },
    components: {
        'app-header': require('components/header.vue'),
        'sidebar': require('components/sidebar.vue')
    },
    events: {
        'navigation:toggled': function() {
            $("body").toggleClass('sidebar-collapse');
            $("body").toggleClass('sidebar-open');
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
        this.fix_size();
        this.slimscroll();

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
         * Fix sidebar size
         */
        fix_size() {
            //Get window height and the wrapper height
            var neg = this.$find('.main-header').height() + this.$find('.main-footer').height();
            var window_height = $(window).height();
            var sidebar_height = this.$find('.main-sidebar').height();
            //Set the min-height of the content and sidebar based on the
            //the maximum height of the document.
            if (window_height >= sidebar_height) {
                this.$find('.content-wrapper, .main-sidebar').css('min-height', window_height - neg);
            } else {
                this.$find('.content-wrapper, .main-sidebar').css('min-height', sidebar_height);
            }
        },

        /**
         * Enable slimscroll on sidebar
         */
        slimscroll() {
            this.$find('.sidebar').slimscroll({
                height: ($(window).height() - this.$find('.main-header').height()) + 'px',
                color: 'rgba(0, 0, 0, 0.2)',
                size: '3px'
            });
        },

        /**
         * Insert a modal Vue in the application.
         * @param  {Object} options     The modal component definition (options passed to Vue.extend())
         * @param  {Object} data        Data to assign to modal properties
         * @return {Vue}                The child instanciated vm
         */
        $modal(options, data) {
            let constructor = Vue.extend(options);
            return new constructor({
                el: this.$els.modal,
                parent: this,
                data: data
            });
        }
    }
};
</script>
