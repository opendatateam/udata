<!-- sidebar: style can be found in sidebar.less -->
<template>
<aside class="main-sidebar">
    <scrollbox v-ref:scrollbox>
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
    </scrollbox>
</aside>
</template>

<script>
import i18n from 'i18n';
import SidebarMenuItem from 'components/sidebar-menu-item.vue';
import Scrollbox from 'components/scrollbox/index.vue';

const MENU = [{
    label: i18n._('Dashboard'),
    icon: 'dashboard',
    route: '/'
}, {
    label: i18n._('Profile'),
    icon: 'male',
    route: '/me/',
    children: [{
        label: i18n._('Dataset'),
        icon: 'cubes',
        scrollTo: '#datasets'
    }, {
        label: i18n._('Reuses'),
        icon: 'recycle',
        scrollTo: '#reuses'
    }]
}];
const BOTTOM_MENU = [{
    label: i18n._('Site'),
    icon: 'globe',
    route: '/site/',
    children: [{
        label: i18n._('Dataset'),
        icon: 'cubes',
        scrollTo: '#datasets'
    }, {
        label: i18n._('Reuses'),
        icon: 'recycle',
        scrollTo: '#reuses'
    }, {
        label: i18n._('Organizations'),
        icon: 'building',
        scrollTo: '#organizations'
    }, {
        label: i18n._('Users'),
        icon: 'group',
        scrollTo: '#users'
    }]
}, {
    label: i18n._('Editorial'),
    icon: 'newspaper-o',
    route: '/editorial/'
}, {
    label: i18n._('System'),
    icon: 'cogs',
    route: '/system/'
}];

export default {
    name: 'sidebar',
    components: {SidebarMenuItem, Scrollbox},
    data() {
        return {
            search_label: `${this._('Search')}…`,
        };
    },
    computed: {
        menu() {
            const menu = MENU.concat(this.organizations_menus);
            return this.$root.me.has_role('admin') ? menu.concat(BOTTOM_MENU) : menu;
        },
        organizations_menus() {
            if (!this.$root.me.organizations) {
                return [];
            }
            return this.$root.me.organizations.map(org => {
                return {
                    label: org.acronym || org.name,
                    image: org.logo_thumbnail,
                    route: `/organization/${org.id}/`,
                    children: [{
                        label: this._('Dataset'),
                        icon: 'cubes',
                        scrollTo: '#datasets-widget'
                    }, {
                        label: this._('Reuses'),
                        icon: 'recycle',
                        scrollTo: '#reuses-widget'
                    }, {
                        label: this._('Discussions'),
                        icon: 'comment',
                        scrollTo: '#reuses-widget'
                    }]
                };
            });
        }
    },
    ready() {
        this.$refs.scrollbox.calculateSize();
    },
    methods: {
        onSearch() {
            const terms = this.$els.terms.value;
            if (terms && terms.length > 2) {
                this.$go({name: 'search', query: { q: terms }});
            }
        }
    },
    watch: {
        // Sidebar height can change on route change
        // because some routes collapse or expand the menu
        $route() {
            this.$refs.scrollbox.calculateSize();
        },
        // Sidebar height change on menu change
        menu() {
            this.$refs.scrollbox.calculateSize();
        }
    }
};
</script>

<style lang="less">
.main-sidebar {
    height: 100%;

    .scrollbox__wrapper {
        height: 100%;
    }
}
</style>
