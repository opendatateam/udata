<!-- style can be found in sidebar.less -->
<style lang="less">
// Vars extracted from adminlte/vars.less
@hover-bg: #f9f9f9;


.sidebar {
    li {
        border: 0;
    }

    .menu-item {
        margin: 0;
        padding: 0;
        cursor: pointer;

        > a {
            padding: 12px 5px 12px 15px;
            margin-right: 1px;
            display: block;

            > .fa, > .glyphicon, > .ion {
                width: 20px;
            }

            img {
                width: 20px;
                height: 20px;
                border: 1px solid #333;
            }
        }

        > a:hover, &.active > a {
            color: #222;
            background-color: @hover-bg;
        }

        .treeview-menu {
            display: block;
            margin: 0 1px;
            .menu-item {
                margin: 0;
                background-color: @hover-bg;

                > a {
                    color: #777;
                    padding: 5px 5px 5px 20px;
                    display: block;
                    font-size: 14px;
                    margin: 0px 0px;

                    &:hover {
                        color: #111;
                    }
                }
            }
        }
    }
}
</style>

<template>
<li class="menu-item" v-class="treeview:children, active: active">
    <a v-on="click: click">
        <i v-if="icon" class="fa fa-fw fa-{{icon}}"></i>
        <img v-if="image" v-attr="src:image" />
        <span class="text-overflow">{{ label | truncate 25 }}</span>
        <i v-if="is_tree" class="fa fa-angle-{{open ? 'down' : 'left'}} pull-right"></i>
        <small v-if="badge" class="badge pull-right bg-{{badge-color}}">{{badge.label}}</small>
    </a>
    <ul v-if="is_tree" v-show="open" class="treeview-menu">
        <li v-repeat="children" v-component="sidebar-menu-item"></li>
    </ul>
</li>
</template>

<script>
'use strict';

module.exports = {
    name: 'sidebar-menu-item',
    replace: true,
    data: function() {
        return {
            open: false,
        };
    },
    computed: {
        is_tree: function() {
            return this.children && this.children.length;
        },
        active: function() {
            return this.open || this.$router.current_route && this.route === this.$router.current_route;
        }
    },
    methods: {
        click: function() {
            if (this.is_tree) {
                this.open = !this.open;
            } else {
                this.$go(this.route);
            }
        }
    }
};
</script>
