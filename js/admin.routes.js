import Vue from 'vue';
import VueRouter from 'vue-router';
import config from 'config';

Vue.use(VueRouter)

const router = new VueRouter({
    history: true,
    root: config.root
});

router.map({
    '/': {
        component: function(resolve) {
            require(['./views/home.vue'], resolve);
        }
    },
    '/me/': {
        component: function(resolve) {
            require(['./views/me.vue'], resolve);
        }
    },
    '/site/': {
        component: function(resolve) {
            require(['./views/site.vue'], resolve);
        }
    },
    '/dataset/new/': {
        component: function(resolve) {
            require(['./views/dataset-wizard.vue'], resolve);
        }
    },
    '/dataset/new/:oid/': {
        component: function(resolve) {
            require(['./views/dataset-wizard.vue'], resolve);
        },
        callback: function(view) {
            if (!view.dataset.id) {
                view.dataset.fetch(oid);
            }
        }
    },
    '/dataset/new/:oid/share': {
        component: function(resolve) {
            require(['./views/dataset-wizard.vue'], resolve);
        },
        callback: function(view) {
            if (!view.dataset.id) {
                view.dataset.fetch(oid);
            }
        }
    },
    '/dataset/:oid/': {
        name: 'dataset',
        component: function(resolve) {
            require(['./views/dataset.vue'], resolve);
        },
        subRoutes: {
            'issue/:issue_id/': {
                name: 'dataset-issue',
                component: function(resolve) {
                    require(['./components/issues/modal.vue'], resolve);
                }
            },
            'discussion/:discussion_id/': {
                name: 'dataset-discussion',
                component: function(resolve) {
                    require(['./components/discussions/modal.vue'], resolve);
                }
            },
            'community-resource/:rid/': {
                name: 'dataset-community-resource',
                component: function(resolve) {
                    require(['./components/communityresource/edit-modal.vue'], resolve);
                }
            },
            // '/resource/new/': {
            //     name: 'dataset-new-resource',
            //     component: function(resolve) {
            //         require(['./components/dataset/resource/add-modal.vue'], resolve);
            //     }
            // },
            // '/resource/:rid/': {
            //     name: 'dataset-resource',
            //     component: function(resolve) {
            //         require(['./components/dataset/resource/resource-modal.vue'], resolve);
            //     }
            // }
        }
    },
    '/community-resource/new/': {
        component: function(resolve) {
            require(['./views/community-resource-wizard.vue'], resolve);
        }
    },
    '/reuse/new/': {
        component: function(resolve) {
            require(['./views/reuse-wizard.vue'], resolve);
        }
    },
    '/reuse/:oid/': {
        name: 'reuse',
        component: function(resolve) {
            require(['./views/reuse.vue'], resolve);
        },
        subRoutes: {
            'issue/:issue_id/': {
                name: 'reuse-issue',
                component: function(resolve) {
                    require(['./components/issues/modal.vue'], resolve);
                }
            },
            'discussion/:discussion_id/': {
                name: 'reuse-issue',
                component: function(resolve) {
                    require(['./components/discussions/modal.vue'], resolve);
                }
            }
        }
    },
    '/organization/new/': {
        component: function(resolve) {
            require(['./views/organization-wizard.vue'], resolve);
        }
    },
    '/organization/new/:oid/': {
        component: function(resolve) {
            require(['./views/organization-wizard.vue'], resolve);
        },
        callback: function(view) {
            if (!view.organization.id) {
                view.organization.fetch(oid);
            }
        }
    },
    '/organization/:oid/': {
        name: 'organization',
        component: function(resolve) {
            require(['./views/organization.vue'], resolve);
        }
    },
    '/user/:oid/': {
        name: 'user',
        component: function(resolve) {
            require(['./views/user.vue'], resolve);
        }
    },
    '/harvester/new/': {
        component: function(resolve) {
            require(['./views/harvester-wizard.vue'], resolve);
        }
    },
    '/harvester/:oid/': {
        name: 'harvester',
        component: function(resolve) {
            require(['./views/harvester.vue'], resolve);
        }
    },
    '/harvester/:oid/edit': {
        component: function(resolve) {
            require(['./views/harvester-edit.vue'], resolve);
        }
    },
    '/post/new/': {
        component: function(resolve) {
            require(['./views/post-wizard.vue'], resolve);
        }
    },
    '/post/:oid/': {
        component: function(resolve) {
            require(['./views/post.vue'], resolve);
        }
    },
    '/topic/new/': {
        component: function(resolve) {
            require(['./views/topic-wizard.vue'], resolve);
        }
    },
    '/topic/:oid/': {
        component: function(resolve) {
            require(['./views/topic.vue'], resolve);
        }
    },
    '/editorial/': {
        component: function(resolve) {
            require(['./views/editorial.vue'], resolve);
        }
    },
    '/system/': {
        component: function(resolve) {
            require(['./views/system.vue'], resolve);
        }
    },
    '/search/': {
        name: 'search',
        component: function(resolve) {
            require(['./views/search.vue'], resolve);
        }
    }
});


/**
 * Make the $go shortcut available on every view instance.
 */
Vue.prototype.$go = function(route) {
    return router.go(route);
};

export default router;
