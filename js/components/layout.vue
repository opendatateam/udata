<style lang="less">
.content-header {
    h1 a {
        color: black;

        .fa {
            font-size: 0.4em;
        }
    }
}
</style>

<template>
<div class="content-wrapper">
    <!-- Routable modals should be inserted here
        Wait for feedback or implementation on named outlets.
        See: https://github.com/vuejs/vue-router/issues/213
    -->
    <router-view></router-view>
    <!-- Content Header (Page header) -->
    <section class="content-header">
        <div class="btn-group btn-group-sm btn-actions pull-right clearfix">
            <div v-if="menu_actions" class="btn-group btn-group-sm" role="group">
                <button type="button" class="btn btn-info dropdown-toggle" data-toggle="dropdown">
                    {{_('Edit')}}
                    <span class="caret"></span>
                </button>
                <ul class="dropdown-menu dropdown-menu-right" role="menu">
                    <li v-for="action in menu_actions"
                         :role="action.divider ? 'separator' : false"
                         :class="{ 'divider': action.divider }">
                        <a class="pointer"
                            v-if="!action.divider"
                            @click="action.method" >
                            <span v-if="action.icon" class="fa fa-fw fa-{{action.icon}}"></span>
                            {{action.label}}
                        </a>
                    </li>
                </ul>
            </div>
        </div>
        <h1>
            <a v-if="page" :href="page" :title="_('See on the site')">
                {{ title }}
                <span class="fa fa-external-link"></span>
            </a>
            <span v-if="!page">{{title}}</span>

            <small v-if="subtitle">{{subtitle}}</small>
            <small v-if="badges">
                <span v-for="badge in badges"
                    class="label label-{{badge.class}}">{{badge.label}}</span>
            </small>
        </h1>
    </section>
    <!-- Notifications -->
    <notification-zone></notification-zone>
    <!-- Main content -->
    <section class="content">
        <slot></slot>
    </section>
</div>
</template>

<script>
import NotificationZone from 'components/notification-zone.vue';

export default {
    name: 'layout',
    props: {
        title: String,
        subtitle: String,
        page: String,
        actions: {
            type: Array,
            default: () => [],
        },
        badges: Array
    },
    components: {NotificationZone},
    computed: {
        menu_actions() {
            if (this.actions && this.actions.length > 1) {
                return this.actions;
            }
        }
    }
};
</script>
