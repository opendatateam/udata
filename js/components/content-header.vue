<style lang="less">
// Content Header
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
</style>
<template>
    <section class="content-header">
        <h1>
            {{$root.meta.title}}
            <div v-if="$root.meta.actions && $root.meta.actions.length"
                class="btn-group" role="group">
                <a class="btn btn-link btn-sm dropdown-toggle"
                    data-toggle="dropdown" aria-expanded="false">
                    <span class="fa fa-fw fa-gear"></span>
                </a>
                <ul class="dropdown-menu dropdown-menu-right" role="menu">
                    <li v-for="action in $root.meta.actions"
                         :role="action.divider ? 'separator' : false"
                         :class="{ 'divider': action.divider }">
                        <a class="pointer"
                            v-if="!action.divider"
                            @click="action_click(action)" >
                            <span v-if="action.icon" class="fa fa-fw fa-{{action.icon}}"></span>
                            {{action.label}}
                        </a>
                    </li>
                </ul>
            </div>
            <small v-if="$root.meta.subtitle">{{$root.meta.subtitle}}</small>
            <small v-if="$root.meta.badges">
                <span v-for="badge in $root.meta.badges"
                    class="label label-{{badge.class}}">{{badge.label}}</span>
            </small>
        </h1>
        <div class="btn-group btn-group-sm btn-actions pull-right clearfix"
            v-if="$root.meta.page">
            <a class="btn btn-link" :href="$root.meta.page"
                :title="_('See it as viewed by visitors')">
                {{ _('See on the site') }} →
            </a>
        </div>
    </section>
</template>

<script>
export default {
    name: 'content-header',
    replace: true,
    methods: {
        action_click: function(action) {
            if (action.method && this.$root.$.content.hasOwnProperty(action.method)) {
                this.$root.$.content[action.method]();
            }
        }
    }
};
</script>
