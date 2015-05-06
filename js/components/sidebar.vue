<!-- sidebar: style can be found in sidebar.less -->
<template>
    <section class="sidebar">
        <!-- search form -->
        <div class="sidebar-form">
            <form method="get">
                <div class="input-group">
                    <input type="text" name="q" class="form-control" placeholder="{{'Search'|i18n}}..." />
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
            <sidebar-menu-item v-repeat="menu"></sidebar-menu-item>
        </ul>

    </section>
</template>

<script>
'use strict';

var Vue = require('vue'),
    MENU = [{
        'label': Vue._('Dashboard'),
        'icon': 'dashboard',
        'route': '/'
    }, {
        'label': Vue._('Me'),
        'icon': 'male',
        'route': '/me/'
    }],
    bottom_menu = [{
        'label': Vue._('Site'),
        'icon': 'globe',
        'route': '/site/'
    }, {
        'label': Vue._('Editorial'),
        'icon': 'newspaper-o',
        'route': '/editorial/'
    }, {
        'label': Vue._('System'),
        'icon': 'cogs',
        'route': '/system/'
    }];
    // 'children': [{
    //     'label': 'Home page',
    //     'icon': 'home',
    //     'route': '/homepage/'
    // }, {
    //     'label': 'Thème',
    //     'icon': 'eyedropper',
    //     'route': '/theme/'
    // }, {
    //     'label': 'Thématiques',
    //     'icon': 'book',
    //     'route': '/topics/'
    // }, {
    //     'label': 'Articles',
    //     'icon': 'newspaper-o',
    //     'route': '/posts/'
    // }]

module.exports = {
    components: {
        'sidebar-menu-item': require('components/sidebar-menu-item.vue')
    },
    computed: {
        menu: function() {
            var menu = MENU.concat(this.organizations_menus);
            return this.$root.me.has_role('admin') ? menu.concat(bottom_menu) : menu;
        },
        user_menu: function() {
            return ;
        },
        organizations_menus: function() {
            if (!this.$root.me.organizations) {
                return [];
            }
            return this.$root.me.organizations.map(function(org) {
                return {
                    'label': org.name,
                    'image': org.logo,
                    'route': '/organization/' + org.id + '/'
                };
            });
        }
    }
};
</script>
