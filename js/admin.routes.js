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
        name: 'dataset',
        component: view('dataset'),
        subRoutes: {
            'issue/:issue_id/': {
                name: 'dataset-issue',
                component: modal('issues/modal')
            },
            'discussion/:discussion_id/': {
                name: 'dataset-discussion',
                component: modal('discussions/modal')
            },
            'community-resource/:rid/': {
                name: 'dataset-community-resource',
                component: modal('communityresource/edit-modal')
            },
            // '/resource/new/': {
            //     name: 'dataset-new-resource',
            //     component: modal('dataset/resource/add-modal')
            // },
            // '/resource/:rid/': {
            //     name: 'dataset-resource',
            //     component: modal('dataset/resource/resource-modal')
            // }
        }
    },
    '/community-resource/new/': {
        component: view('community-resource-wizard')
    },
    '/reuse/new/': {
        component: view('reuse-wizard')
    },
    '/reuse/:oid/': {
        name: 'reuse',
        component: view('reuse'),
        subRoutes: {
            'issue/:issue_id/': {
                name: 'reuse-issue',
                component: modal('issues/modal')
            },
            'discussion/:discussion_id/': {
                name: 'reuse-issue',
                component: modal('discussions/modal')
            }
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
        name: 'organization',
        component: view('organization')
    },
    '/user/:oid/': {
        name: 'user',
        component: view('user')
    },
    '/harvester/new/': {
        component: view('harvester-wizard')
    },
    '/harvester/:oid/': {
        name: 'harvester',
        component: view('harvester')
    },
    '/harvester/:oid/edit': {
        component: view('harvester-edit')
    },
    '/post/new/': {
        component: view('post-wizard')
    },
    '/post/:oid/': {
        component: view('post')
    },
    '/topic/new/': {
        component: view('topic-wizard')
    },
    '/topic/:oid/': {
        component: view('topic')
    },
    '/editorial/': {
        component: view('editorial')
    },
    '/system/': {
        component: view('system')
    }
});


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

/**
 * Asynchronously load model mald (Webpack Lazy loading compatible)
 * @param  {string}   name     the filename (basename) of the view to load.
 */
function modal(name) {
    return function(resolve) {
        require(['./components/'+name+'.vue'], resolve);
    }
};

export default router;
