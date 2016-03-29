<!-- sidebar: style can be found in sidebar.less -->
<template>
    <section class="sidebar">
        <!-- search form -->
        <div class="sidebar-form">
            <form method="get" @submit.prevent="onSearch">
                <div class="input-group">
                    <input type="text" name="q" class="form-control"
                        :placeholder="search_label" v-el:terms />
                    <span class="input-group-btn">
                        <button type="submit" name="search" id="search-btn" class="btn btn-flat">
                            <i class="fa fa-search"></i>
                        </button>
                    </span>
                </div>
            </form>
        </div>
        <!-- End form -->

        <ul class="sidebar-menu">
            <sidebar-menu-item v-for="item in menu"
                :label="item.label"
                :icon="item.icon"
                :image="item.image"
                :route="item.route"
                :badge="item.badge"
                :scroll-to="item.scrollTo"
                :children="item.children">
            </sidebar-menu-item>
        </ul>

    </section>
</template>

<script>
import Vue from 'vue';

const MENU = [{
        label: Vue._('Dashboard'),
        icon: 'dashboard',
        route: '/'
    }, {
        label: Vue._('Me'),
        icon: 'male',
        route: '/me/',
        children: [{
            label: Vue._('Dataset'),
            icon: 'cubes',
            scrollTo: '#datasets'
        }, {
            label: Vue._('Reuses'),
            icon: 'retweet',
            scrollTo: '#reuses'
        }]
    }],
    bottom_menu = [{
        label: Vue._('Site'),
        icon: 'globe',
        route: '/site/',
        children: [{
            label: Vue._('Dataset'),
            icon: 'cubes',
            scrollTo: '#datasets'
        }, {
            label: Vue._('Reuses'),
            icon: 'retweet',
            scrollTo: '#reuses'
        }, {
            label: Vue._('Organizations'),
            icon: 'building',
            scrollTo: '#organizations'
        }, {
            label: Vue._('Users'),
            icon: 'group',
            scrollTo: '#users'
        }]
    }, {
        label: Vue._('Editorial'),
        icon: 'newspaper-o',
        route: '/editorial/'
    }, {
        label: Vue._('System'),
        icon: 'cogs',
        route: '/system/'
    }];

export default {
    components: {
        'sidebar-menu-item': require('components/sidebar-menu-item.vue')
    },
    data() {
        return {
            search_label: this._('Search') + '...'
        };
    },
    computed: {
        menu() {
            var menu = MENU.concat(this.organizations_menus);
            return this.$root.me.has_role('admin') ? menu.concat(bottom_menu) : menu;
        },
        organizations_menus() {
            if (!this.$root.me.organizations) {
                return [];
            }
            return this.$root.me.organizations.map(function(org) {
                return {
                    label: org.acronym || org.name,
                    image: org.logo,
                    route: '/organization/' + org.id + '/',
                    children: [{
                        label: Vue._('Dataset'),
                        icon: 'cubes',
                        scrollTo: '#datasets-widget'
                    }, {
                        label: Vue._('Reuses'),
                        icon: 'retweet',
                        scrollTo: '#reuses-widget'
                    }, {
                        label: Vue._('Issues'),
                        icon: 'warning',
                        scrollTo: '#issues-widget'
                    }, {
                        label: Vue._('Discussions'),
                        icon: 'comment',
                        scrollTo: '#reuses-widget'
                    }]
                };
            });
        }
    },
    methods: {
        onSearch() {
            const terms = this.$els.terms.value;
            if (terms && terms.length > 2) {
                this.$go({name: 'search', query: { q: terms }});
            }
        }
    }
};
</script>
