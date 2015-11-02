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

        .dropdown-menu {
            border-radius: 0;
        }
    }
}

.notification-zone {
    padding: 15px 15px 0;

    .alert {
        &:last-child {
            margin-bottom: 0;
        }

        &:not(:last-child) {
            margin-bottom: 5px;
        }
    }
}
</style>

<template>
<div class="content-wrapper">
    <!-- Content Header (Page header) -->
    <section class="content-header">
        <h1>
            {{title}}
            <div v-if="actions.length"
                class="btn-group" role="group">
                <a class="btn btn-link btn-sm dropdown-toggle"
                    data-toggle="dropdown" aria-expanded="false">
                    <span class="fa fa-fw fa-gear"></span>
                </a>
                <ul class="dropdown-menu dropdown-menu-right" role="menu">
                    <li v-for="action in actions"
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
            <small v-if="subtitle">{{subtitle}}</small>
            <small v-if="badges">
                <span v-for="badge in badges"
                    class="label label-{{badge.class}}">{{badge.label}}</span>
            </small>
        </h1>
        <div class="btn-group btn-group-sm btn-actions pull-right clearfix"
            v-if="page">
            <a class="btn btn-link" :href="page"
                :title="_('See it as viewed by visitors')">
                {{ _('See on the site') }} →
            </a>
        </div>
    </section>
    <!-- Notifications -->
    <div v-if="$root.notifications.length > 0" class="notification-zone">
        <alert v-for="n in $root.notifications" :alert="n"></alert>
    </div>
    <!-- Main content -->
    <section class="content">
        <slot></slot>
    </section>
</div>
</template>

<script>
import Alert from 'components/alert.vue';

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
    components: {
        Alert
    }
};
</script>
