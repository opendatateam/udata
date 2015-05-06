<style lang="less">
a.sidebar-toggle {
    cursor: pointer;
}
</style>
<template>
    <a v-route="/" class="logo">
      <!-- Add the class icon to your logo image or logo icon to add the margining -->
      {{$root.site.title}}
    </a>
    <!-- Header Navbar: style can be found in header.less -->
    <nav class="navbar navbar-static-top" role="navigation">
        <!-- Sidebar toggle button-->
        <a class="sidebar-toggle" data-toggle="offcanvas" role="button" v-on="click: click($event)">
            <span class="sr-only">Toggle navigation</span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
            <span class="icon-bar"></span>
        </a>
      <div class="navbar-custom-menu">
          <ul class="nav navbar-nav">
              <li class="dropdown notifications-menu" v-component="notification-menu"></li>
              <!-- New actions: style can be found in dropdown.less -->
              <li class="dropdown add-menu notifications-menu" v-component="add-menu"></li>
              <!-- User Account: style can be found in dropdown.less -->
              <li class="dropdown user user-menu" v-component="user-menu"></li>
          </ul>
        </div>
    </nav>
</template>


<script>
'use strict';

module.exports = {
    components: {
        'user-menu': require('components/user-menu.vue'),
        'notification-menu': require('components/notification-menu.vue'),
        'add-menu': require('components/add-menu.vue')
    },
    methods: {
        click: function(e) {
            e.preventDefault();
            this.$dispatch('navigation:toggled');
        }
    }
};
</script>
