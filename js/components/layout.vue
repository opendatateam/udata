<style lang="less">
.content-header {

    > .btn-actions {
        background: transparent;
        margin-top: 0px;
        margin-bottom: 0;
        position: absolute;
        top: 15px;
        right: 10px;

        .btn-link {
            color: lighten(black, 45%);
            font-size: 1.2em;
            padding: 5px;

            &:hover {
                color: lighten(black, 20%);
            }
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
        <h1>
            {{title}}
            <small v-if="subtitle">{{subtitle}}</small>
            <small v-if="badges">
                <span v-for="badge in badges"
                    class="label label-{{badge.class}}">{{badge.label}}</span>
            </small>
        </h1>
        <div class="btn-toolbar btn-actions pull-right clearfix">
            <div v-if="main_action" class="btn-group btn-group-sm">
                <div v-if="menu_actions" class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-info" @click="main_action.method">
                        <span v-if="main_action.icon" class="fa fa-fw fa-{{main_action.icon}}"></span>
                        {{main_action.label}}
                    </button>
                    <button type="button" class="btn btn-info dropdown-toggle" data-toggle="dropdown">
                        <span class="caret"></span>
                        <span class="sr-only">Toggle Dropdown</span>
                    </button>
                    <ul class="dropdown-menu" role="menu">
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
                <button v-if="!menu_actions" type="button" class="btn btn-info btn-sm">
                    <span v-if="action.icon" class="fa fa-fw fa-{{action.icon}}"></span>
                    {{main_action.label}}
                </button>
            </div>
            <div class="btn-group btn-group-sm" v-if="page">
                <a class="btn btn-link" :href="page" :title="_('See it as viewed by visitors')">
                    {{ _('See on the site') }} →
                </a>
            </div>
        </div>
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
    name: 'DashboardLayout',
    props: {
        title: String,
        subtitle: String,
        page: String,
        actions: {
            type: Array,
            default() {return []}
        },
        badges: Array
    },
    components: {NotificationZone},
    computed: {
        main_action() {
            if (this.actions) {
                return this.actions[0];
            }
        },
        menu_actions() {
            if (this.actions && this.actions.length > 1) {
                return this.actions.slice(1);
            }
        }
    }
};
</script>
