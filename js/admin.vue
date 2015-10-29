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
    <div v-el="modal"></div>
    <app-header class="main-header"></app-header>
    <sidebar class="main-sidebar"></sidebar>
    <div class="content-wrapper">
        <!-- Content Header (Page header) -->
        <content-header meta="{{meta}}"></content-header>
        <!-- Notifications -->
        <div v-if="notifications.length > 0" class="notification-zone">
            <alert-box v-repeat="notifications"></alert-box>
        </div>
        <!-- Main content -->
        <section class="content">
            <component v-ref="content" :is="view"></component>
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
            view: null,
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
    routes: {
        '/': function() {
            this.loadView('home');
        },
        '/me/': function() {
            this.loadView('me');
        },
        '/site/': function() {
            this.loadView('site');
        },
        '/dataset/new/': function() {
            this.loadView('dataset-wizard');
        },
        '/dataset/new/:oid/': function(oid) {
            this.loadView('dataset-wizard', function(view) {
                if (!view.dataset.id) {
                    view.dataset.fetch(oid);
                }
            });
        },
        '/dataset/new/:oid/share': function(oid) {
            this.loadView('dataset-wizard', function(view) {
                if (!view.dataset.id) {
                    view.dataset.fetch(oid);
                }
            });
        },
        '/dataset/:oid/': function(dataset_id) {
            this.loadView('dataset', function(view) {
                view.dataset_id = dataset_id;
            });
        },
        '/community-resource/new/': function() {
            this.loadView('community-resource-wizard');
        },
        '/reuse/new/': function() {
            this.loadView('reuse-wizard');
        },
        '/reuse/:oid/': function(reuse_id) {
            this.loadView('reuse', function(view) {
                view.reuse_id = reuse_id;
            });
        },
        '/organization/new/': function() {
            this.loadView('organization-wizard');
        },
        '/organization/new/:oid/': function(oid) {
            this.loadView('organization-wizard', function(view) {
                if (!view.organization.id) {
                    view.organization.fetch(oid);
                }
            });
        },
        '/organization/:oid/': function(org_id) {
            this.loadView('organization', function(view) {
                view.org_id = org_id;
            });
        },
        '/user/:oid/': function(user_id) {
            this.loadView('user', function(view) {
                view.user_id = user_id;
            });
        },
        '/harvester/new/': function() {
            this.loadView('harvester-wizard');
        },
        '/harvester/:oid/': function(source_id) {
            this.loadView('harvester', function(view) {
                view.source_id = source_id;
            });
        },
        '/harvester/:oid/edit': function(source_id) {
            this.loadView('harvester-edit', function(view) {
                view.source_id = source_id;
            });
        },
        '/post/new/': function() {
            this.loadView('post-wizard');
        },
        '/post/:oid/': function(post_id) {
            this.loadView('post', function(view) {
                view.post_id = post_id;
            });
        },
        '/topic/new/': function() {
            this.loadView('topic-wizard');
        },
        '/topic/:oid/': function(topic_id) {
            this.loadView('topic', function(view) {
                view.topic_id = topic_id;
            });
        },
        '/editorial/': function() {
            this.loadView('editorial');
        },
        '/system/': function() {
            this.loadView('system');
        },
        '/issue/:oid/': function(issue_id) {
            var m = this.$modal({data: {
                        issueid: issue_id
                    }},
                    Vue.extend(require('components/issues/modal.vue'))
                );
        },
        '/discussion/:oid/': function(discussion_id) {
            var m = this.$modal({data: {
                        discussionid: discussion_id
                    }},
                    Vue.extend(require('components/discussions/modal.vue'))
                );
        }
    },
    watch: {
        'view': function(view, old) {
            this.meta = emptyMeta();
            Vue.nextTick(() => {
                if (this.$.content.meta) {
                    Object.assign(this.meta, this.$.content.meta);
                }
            });
        }
    },
    attached: function() {
        this.$router.init();
    },
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
         * @param  {Vue} constructor    An optionnal Vue constrcutor (ie. Vue.extend())
         * @return {[type]}             [description]
         */
        $modal: function(options, constructor) {
            options.el = this.$$.modal;
            return this.$addChild(options, constructor);
        },

        /**
         * Asynchronously load view (Webpack Lazy loading compatible)
         * @param  {string}   name     the filename (basename) of the view to load.
         * @param  {Function} callback An optionnal callback executed
         *                             in the application scope when
         *                             the view is loaded
         */
        loadView: function(name, callback) {

            let cb = () => {
                callback.apply(this, [this.$.content]);
            };

            if (this.$options.components.hasOwnProperty(name)) {
                this.view = name;
                if (callback) {
                    this.$nextTick(cb);
                }
            } else {
                require(['./views/' + name + '.vue'], (options) => {
                    this.$options.components[name] = Vue.extend(options);
                    this.view = name;
                    if (callback) {
                        this.$nextTick(cb);
                    }
                });
            }
        }
    }
};
</script>
