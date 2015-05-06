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
            <small v-if="$root.meta.subtitle">{{$root.meta.subtitle}}</small>
        </h1>
        <div class="btn-group  btn-group-sm btn-actions pull-right clearfix">
            <a v-if="$root.meta.page" class="btn btn-link" href="{{$root.meta.page}}"
                title="{{ _('See on the site') }}">
                <span class="fa fa-fw fa-bookmark"></span>
            </a>
            <div v-if="$root.meta.actions && $root.meta.actions.length"
                class="btn-group" role="group">
                <a class="btn btn-link btn-sm dropdown-toggle"
                    data-toggle="dropdown" aria-expanded="false">
                    <span class="fa fa-fw fa-gear"></span>
                </a>
                <ul class="dropdown-menu dropdown-menu-right" role="menu">
                    <li v-repeat="action:$root.meta.actions">
                        <a v-on="click: action_click(action)" class="pointer">
                            <span v-if="action.icon" class="fa fa-fw fa-{{action.icon}}"></span>
                            {{action.label}}
                        </a>
                    </li>
                </ul>
            </div>
        </div>
    </section>
</template>

<script>
'use strict';

module.exports = {
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
