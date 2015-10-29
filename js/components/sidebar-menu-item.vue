<!-- style can be found in sidebar.less -->
<style lang="less">
.sidebar-menu {
    > li {
        cursor: pointer;

        > a {
            img {
                width: 20px;
                height: 20px;
                border: 1px solid #333;
            }
        }
    }
}
</style>

<template>
<li :class="{ 'treeview': children, 'active': active }">
    <a @click="click">
        <i v-if="icon" class="fa fa-fw fa-{{icon}}"></i>
        <img v-if="image" v-attr="src:image" />
        <span>{{ label | truncate 25 }}</span>
        <i v-if="is_tree" class="fa fa-angle-{{open ? 'down' : 'left'}} pull-right"></i>
        <small v-if="badge" class="badge pull-right bg-{{badge-color}}">{{badge.label}}</small>
    </a>
    <ul v-if="is_tree" v-show="open" class="treeview-menu">
        <sidebar-menu-item v-repeat="children"></sidebar-menu-item>
    </ul>
</li>
</template>

<script>
export default {
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
