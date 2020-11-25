<template>
<li class="dropdown add-menu notifications-menu" v-show="!readOnlyEnabled">
    <a href="#" class="dropdown-toggle" data-toggle="dropdown">
        <i class="fa fa-plus"></i>
    </a>
    <ul class="dropdown-menu">
        <li class="header text-center" v-i18n="Add"></li>
        <li>
            <!-- inner menu: contains the actual data -->
            <ul class="menu">
                <li v-for="action in actions">
                    <a v-link="action.route">
                        <span class="fa fa-fw {{action.icon}} text-{{action.color}}"></span>
                        <span>{{ action.label }}</span>
                    </a>
                </li>
            </ul>
        </li>
    </ul>
</li>
</template>

<script>
import config from 'config';

export default {
    name: 'add-menu',
    data() {
        return {
            readOnlyEnabled: config.read_only_enabled && !config.user.roles.includes('admin')
        }
    },
    computed: {
        actions() {
            var actions = [{
                    label: this._('A dataset'),
                    icon: 'fa-cubes',
                    route: '/dataset/new/',
                    color: 'info'
                }, {
                    label: this._('A reuse'),
                    icon: 'fa-recycle',
                    route: '/reuse/new/',
                    color: 'success'
                }, {
                    label: this._('An organization'),
                    icon: 'fa-building',
                    route: '/organization/new/',
                    color: 'warning'
                }, {
                    label: this._('An harvester'),
                    icon: 'fa-tasks',
                    route: '/harvester/new/',
                    color: 'navy'
                }];
            if (this.$root.me.has_role('admin')) {
                actions.push({
                    label: this._('A post'),
                    icon: 'fa-newspaper-o',
                    route: '/post/new/',
                    color: 'purple'
                });
                actions.push({
                    label: this._('A topic'),
                    icon: 'fa-book',
                    route: '/topic/new/',
                    color: 'teal'
                });
            }
            return actions;
        }
    }
};
</script>
