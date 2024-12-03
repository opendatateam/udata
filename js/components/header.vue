<style lang="less">
.main-header {
    a.sidebar-toggle {
        cursor: pointer;

        &::before {
            content: '';
        }
    }
}
</style>
<template>
<div class="main-header">
    <a href="/" class="logo">
      <!-- Add the class icon to your logo image or logo icon to add the margining -->
      <!-- mini logo for sidebar mini 50x50 pixels -->
      <span class="logo-mini"><b>{{$root.site.title ? $root.site.title[0] : ''}}</b></span>
      <!-- logo for regular state and mobile devices -->
      <span class="logo-lg">{{$root.site.title}}</span>
    </a>
    <!-- Header Navbar: style can be found in header.less -->
    <nav class="navbar navbar-static-top">
        <!-- Sidebar toggle button-->
        <a class="sidebar-toggle" role="button" @click="click($event)">
            <span class="sr-only">Toggle navigation</span>
            <span :class="['fa', $root.toggled ? 'fa-angle-double-left' : 'fa-angle-double-right']"></span>
        </a>
        <span class="navbar-banner" v-if="newAdminUrl">
            <a :href="newAdminUrl" target="_blank">
                {{ _("✨ Come and discover the new version of the back office") }}
                <span class="fa fa-external-link"></span>
            </a>
        </span>
      <div class="navbar-custom-menu">
          <ul class="nav navbar-nav">
            <notification-menu></notification-menu>
            <add-menu></add-menu>
            <user-menu></user-menu>
          </ul>
        </div>
    </nav>
</div>
</template>


<script>
'use strict';

module.exports = {
    props: {
        newAdminUrl: String,
    },
    components: {
        'user-menu': require('components/user-menu.vue'),
        'notification-menu': require('components/notification-menu.vue'),
        'add-menu': require('components/add-menu.vue')
    },
    methods: {
        click(e) {
            e.preventDefault();
            this.$dispatch('navigation:toggled');
        }
    }
};
</script>
