import Vue from 'vue';
import VueRouter from 'vue-router';
import config from 'config';

Vue.use(VueRouter)

const router = new VueRouter({history: true, root: config.root});

router.map({
    '/': {
        component: view('home')
    },
    '/me/': {
        component: view('me')
    },
    '/site/': {
        component: view('site')
    },
    '/dataset/new/': {
        component: view('dataset-wizard')
    },
    '/dataset/new/:oid/':{
        component: view('dataset-wizard'),
        callback: function(view) {
            if (!view.dataset.id) {
                view.dataset.fetch(oid);
            }
        }
    },
    '/dataset/new/:oid/share': {
        component: view('dataset-wizard'),
        callback: function(view) {
            if (!view.dataset.id) {
                view.dataset.fetch(oid);
            }
        }
    },
    '/dataset/:oid/': {
        component: view('dataset'),
        callback: function(view) {
            view.dataset_id = dataset_id;
        }
    },
    '/community-resource/new/': {
        component: view('community-resource-wizard')
    },
    '/reuse/new/': {
        component: view('reuse-wizard')
    },
    '/reuse/:oid/': {
        component: view('reuse'),
        callback: function(view) {
            view.reuse_id = reuse_id;
        }
    },
    '/organization/new/': {
        component: view('organization-wizard')
    },
    '/organization/new/:oid/': {
        component: view('organization-wizard'),
        callback: function(view) {
            if (!view.organization.id) {
                view.organization.fetch(oid);
            }
        }
    },
    '/organization/:oid/': {
        component: view('organization'),
        callback: function(view) {
            view.org_id = org_id;
        }
    },
    '/user/:oid/': {
        component: view('user'),
        callback: function(view) {
            view.user_id = user_id;
        }
    },
    '/harvester/new/': {
        component: view('harvester-wizard')
    },
    '/harvester/:oid/': {
        component: view('harvester'),
        callback: function(view) {
            view.source_id = source_id;
        }
    },
    '/harvester/:oid/edit': {
        component: view('harvester-edit'),
        callback: function(view) {
            view.source_id = source_id;
        }
    },
    '/post/new/': {
        component: view('post-wizard')
    },
    '/post/:oid/': {
        component: view('post'),
        callback: function(view) {
            view.post_id = post_id;
        }
    },
    '/topic/new/': {
        component: view('topic-wizard')
    },
    '/topic/:oid/': {
        component: view('topic'),
        callback: function(view) {
            view.topic_id = topic_id;
        }
    },
    '/editorial/': {
        component: view('editorial')
    },
    '/system/': {
        component: view('system')
    },
    // '/issue/:oid/': function(issue_id) {
    //     var m = this.$modal({data: {
    //                 issueid: issue_id
    //             }},
    //             Vue.extend(require('components/issues/modal.vue'))
    //         );
    // },
    // '/discussion/:oid/': function(discussion_id) {
    //     var m = this.$modal({data: {
    //                 discussionid: discussion_id
    //             }},
    //             Vue.extend(require('components/discussions/modal.vue'))
    //         );
    // }
});

// TODO: refactor meta handling
// router.afterEach(function (transition) {
//     console.log('route', transition.to, router.app.$refs, router.app.$els);
//     Object.assign(router.app.meta, router.app.$refs.view.meta);
// });

// // TODO: use the route attribute on each component using it
// router.afterEach(function (transition) {
//     Object.assign(router.app.$refs.view, transition.to.params);
// });


    // },
    // watch: {
    //     'view': function(view, old) {
    //         this.meta = emptyMeta();
    //         Vue.nextTick(() => {
    //             if (this.$refs.content.meta) {
    //                 Object.assign(this.meta, this.$refs.content.meta);
    //             }
    //         });
    //     }
    // }

/**
 * Make the $go shortcut available on every view instance.
 */
Vue.prototype.$go = function(route) {
    return router.go(route);
};


/**
 * Asynchronously load view (Webpack Lazy loading compatible)
 * @param  {string}   name     the filename (basename) of the view to load.
 */
function view(name) {
    return function(resolve) {
        require(['./views/' + name + '.vue'], resolve);
    }
};

export default router;
