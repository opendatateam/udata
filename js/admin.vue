<style lang="less">
.notification-zone {
    padding: 15px 15px 0;

    .alert {
        &:last-child {
            margin-bottom: 0;
        }

        &:not(:last-child) {
            margin-bottom: 5px;
        }
    }
}

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
    <!-- header logo: style can be found in header.less -->
    <div v-el:modal></div>
    <app-header class="main-header"></app-header>
    <sidebar class="main-sidebar"></sidebar>
    <div class="content-wrapper">
        <!-- Content Header (Page header) -->
        <content-header :meta="meta"></content-header>
        <!-- Notifications -->
        <div v-if="notifications.length > 0" class="notification-zone">
            <alert-box v-for="n in notifications"
                :type="n.type" :icon="n.icon" :closable="n.closable">
            </alert-box>
        </div>
        <!-- Main content -->
        <section class="content">
            <router-view></router-view>
        </section>
    </div>
</template>

<script>
import $ from 'jquery';
import Vue from 'vue';
import me from 'models/me';
import site from 'models/site';
import 'jquery-slimscroll';

/**
 * An empty page metadata factory
 * @return {Object} An empty but complete meta object.
 */
function emptyMeta() {
    return {
        title: null,
        subtitle: null,
        page: null,
        breadcrum: [],
        actions: [],
        badges: []
    };
}

export default {
    name: 'App',
    data: function() {
        return {
            me: me,
            site: site,
            config: require('config'),
            meta: emptyMeta(),
            toggled: false,
            notifications: []
        };
    },
    components: {
        'app-header': require('components/header.vue'),
        'sidebar': require('components/sidebar.vue'),
        'content-header': require('components/content-header.vue'),
        'alert-box': require('components/alert.vue'),
    },
    events: {
        'meta:updated': function(meta) {
            this.meta = meta;
        },
        'navigation:toggled': function() {
            $("body").toggleClass('sidebar-collapse');
            $("body").toggleClass('sidebar-open');
        },
        notify: function(notification) {
            this.notifications.push(notification);
        }
    },
    // watch: {
    //     'view': function(view, old) {
    //         this.meta = emptyMeta();
    //         Vue.nextTick(() => {
    //             if (this.$refs.content.meta) {
    //                 Object.assign(this.meta, this.$refs.content.meta);
    //             }
    //         });
    //     }
    // },
    ready: function() {
        this.fix_size();
        this.slimscroll();
    },
    methods: {
        /**
         * Fix sidebar size
         */
        fix_size: function () {
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
        slimscroll: function () {
            this.$find('.sidebar').slimscroll({
                height: ($(window).height() - this.$find('.main-header').height()) + 'px',
                color: 'rgba(0, 0, 0, 0.2)',
                size: '3px'
            });
        },

        /**
         * Insert a modal Vue in the application.
         * @param  {Object} options     Options to pass to the Vue constructor
         * @param  {Vue} constructor    An optionnal Vue constructor (ie. Vue.extend())
         * @return {Vue}                The child instanciated vm
         */
        $modal: function(options, constructor) {
            constructor = constructor || Vue;
            options.el = this.$els.modal;
            options.parent = this;
            return new constructor(options);
        }
    }
};
</script>
