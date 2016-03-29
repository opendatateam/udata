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

    .treeview-menu > li > a {
        padding: 10px 5px 10px 20px;
    }
}
</style>

<template>
<li :class="{ 'treeview': children, 'active': active }">
    <a @click="click">
        <i v-if="icon" class="fa fa-fw fa-{{icon}}"></i>
        <img v-if="image" :src="image" />
        <span>{{ label | truncate 25 }}</span>
        <i v-if="is_tree" class="fa fa-angle-{{active ? 'down' : 'left'}} pull-right"></i>
        <small v-if="badge" class="badge pull-right bg-{{badge-color}}">{{badge.label}}</small>
    </a>
    <ul v-if="is_tree" v-show="active" class="treeview-menu">
        <sidebar-menu-item v-for="item in children"
            :label="item.label"
            :icon="item.icon"
            :image="item.image"
            :route="item.route || route"
            :scroll-to="item.scrollTo"
            :badge="item.badge"
            :children="item.children">
        </sidebar-menu-item>
    </ul>
</li>
</template>

<script>
export default {
    name: 'sidebar-menu-item',
    replace: true,
    props: ['label', 'icon','image', 'route', 'children', 'badge', 'scrollTo'],
    computed: {
        is_tree() {
            return this.children && this.children.length;
        },
        active() {
            return this.$route.path === this.route;
        }
    },
    methods: {
        click() {
            if (this.route) {
                this.$go(this.route);
            }
            // Workaround until https://github.com/vuejs/vue-router/issues/434
            if (this.scrollTo) {
                this.$nextTick(() => {
                    this.$scrollTo(this.scrollTo);
                })
            }
        }
    }
};
</script>
