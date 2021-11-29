import Vue from 'vue';
import VueRouter from 'vue-router';
import config from 'config';

Vue.use(VueRouter);

const router = new VueRouter({
    history: true,
    root: config.admin_root
});

router.map({
    '/': {
        component(resolve) {
            require(['./views/home.vue'], resolve);
        }
    },
    '/me/': {
        name: 'me',
        component(resolve) {
            require(['./views/me.vue'], resolve);
        }
    },
    '/me/edit/': {
        name: 'me-edit',
        component(resolve) {
            require(['./views/me-edit.vue'], resolve);
        }
    },
    '/site/': {
        name: 'site',
        component(resolve) {
            require(['./views/site.vue'], resolve);
        }
    },
    '/dataset/new/': {
        component(resolve) {
            require(['./views/dataset-wizard.vue'], resolve);
        }
    },
    '/dataset/new/:oid/': {
        component(resolve) {
            require(['./views/dataset-wizard.vue'], resolve);
        },
        callback(view) {
            if (!view.dataset.id) {
                view.dataset.fetch(oid);
            }
        }
    },
    '/dataset/new/:oid/share': {
        component(resolve) {
            require(['./views/dataset-wizard.vue'], resolve);
        },
        callback(view) {
            if (!view.dataset.id) {
                view.dataset.fetch(oid);
            }
        }
    },
    '/dataset/:oid/': {
        name: 'dataset',
        component(resolve) {
            require(['./views/dataset.vue'], resolve);
        },
        subRoutes: {
            'discussion/:discussion_id/': {
                name: 'dataset-discussion',
                component(resolve) {
                    require(['./components/discussions/modal.vue'], resolve);
                }
            },
            'community-resource/:rid/': {
                name: 'dataset-community-resource',
                component(resolve) {
                    require(['./components/dataset/resource/modal.vue'], resolve);
                }
            },
            '/resource/:rid/': {
                name: 'dataset-resource',
                component(resolve) {
                    require(['./components/dataset/resource/modal.vue'], resolve);
                }
            },
        }
    },
    '/dataset/:oid/edit/': {
        name: 'dataset-edit',
        component(resolve) {
            require(['./views/dataset-edit.vue'], resolve);
        },
    },
    '/community-resource/new/': {
        component(resolve) {
            require(['./views/community-resource-wizard.vue'], resolve);
        }
    },
    '/reuse/new/': {
        component(resolve) {
            require(['./views/reuse-wizard.vue'], resolve);
        }
    },
    '/reuse/:oid/': {
        name: 'reuse',
        component(resolve) {
            require(['./views/reuse.vue'], resolve);
        },
        subRoutes: {
            'discussion/:discussion_id/': {
                name: 'reuse-discussion',
                component(resolve) {
                    require(['./components/discussions/modal.vue'], resolve);
                }
            }
        }
    },
    '/reuse/:oid/edit/': {
        name: 'reuse-edit',
        component(resolve) {
            require(['./views/reuse-edit.vue'], resolve);
        },
    },
    '/organization/new/': {
        name: 'organization-new',
        component(resolve) {
            require(['./views/organization-wizard.vue'], resolve);
        }
    },
    '/organization/new/:oid/': {
        component(resolve) {
            require(['./views/organization-wizard.vue'], resolve);
        },
        callback(view) {
            if (!view.organization.id) {
                view.organization.fetch(oid);
            }
        }
    },
    '/organization/:oid/': {
        name: 'organization',
        component(resolve) {
            require(['./views/organization.vue'], resolve);
        }
    },
    '/organization/:oid/edit/': {
        name: 'organization-edit',
        component(resolve) {
            require(['./views/organization-edit.vue'], resolve);
        },
    },
    '/user/:oid/': {
        name: 'user',
        component(resolve) {
            require(['./views/user.vue'], resolve);
        }
    },
    '/user/edit/:oid/': {
        name: 'user-edit',
        component(resolve) {
            require(['./views/user-edit.vue'], resolve);
        }
    },
    '/harvester/new/': {
        component(resolve) {
            require(['./views/harvester-wizard.vue'], resolve);
        }
    },
    '/harvester/:oid/': {
        name: 'harvester',
        component(resolve) {
            require(['./views/harvester.vue'], resolve);
        },
        subRoutes: {
            'schedule': {
                name: 'harvester-schedule',
                component(resolve) {
                    require(['./components/harvest/schedule-modal.vue'], resolve);
                }
            }
        }
    },
    '/harvester/:oid/edit': {
        name: 'harvester-edit',
        component(resolve) {
            require(['./views/harvester-edit.vue'], resolve);
        }
    },
    '/post/new/': {
        name: 'post-new',
        component(resolve) {
            require(['./views/post-wizard.vue'], resolve);
        }
    },
    '/post/:oid/': {
        name: 'post',
        component(resolve) {
            require(['./views/post.vue'], resolve);
        }
    },
    '/post/:oid/edit/': {
        name: 'post-edit',
        component(resolve) {
            require(['./views/post-edit.vue'], resolve);
        }
    },
    '/topic/new/': {
        component(resolve) {
            require(['./views/topic-wizard.vue'], resolve);
        }
    },
    '/topic/:oid/': {
        name: 'topic',
        component(resolve) {
            require(['./views/topic.vue'], resolve);
        }
    },
    '/topic/:oid/edit/': {
        name: 'topic-edit',
        component(resolve) {
            require(['./views/topic-edit.vue'], resolve);
        },
    },
    '/editorial/': {
        name: 'editorial',
        component(resolve) {
            require(['./views/editorial.vue'], resolve);
        }
    },
    '/system/': {
        component(resolve) {
            require(['./views/system.vue'], resolve);
        }
    },
    '/search/': {
        name: 'search',
        component(resolve) {
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
