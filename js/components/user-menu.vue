<style lang="less">
.user-body p:last-child {
    margin-bottom: 0;
}
</style>
<template>
<li class="dropdown user user-menu">
    <a href="#" class="dropdown-toggle" data-toggle="dropdown">
        <img :src="$root.me.avatar || placeholder" class="user-image" alt="User Image">
        <span class="hidden-xs">{{$root.me.fullname}}</span>
    </a>
    <ul class="dropdown-menu">
        <!-- User image -->
        <li class="user-header bg-light-blue">
            <img :src="$root.me.avatar || placeholder" class="img-circle" alt="User Image" />
            <p>
                {{$root.me.fullname}}
                <small><span v-i18n="Member since"></span> {{ $root.me.since | dt LL}}</small>
            </p>
        </li>
        <!-- Menu Body -->
        <li v-if="$root.me.about || roles" class="user-body text-center">
            <div v-markdown="$root.me.about"></div>
            <span class="label label-primary" v-for="role in $root.me.roles">{{role}}</span>
        </li>
        <!-- Menu Footer-->
        <li class="user-footer">
            <div class="pull-left">
                <a :href="'/users/' + $root.me.slug" class="btn btn-default btn-flat" v-i18n="Profile"></a>
            </div>
            <div class="pull-right">
                <a href="/logout" class="btn btn-default btn-flat" v-i18n="Sign out"></a>
            </div>
        </li>
    </ul>
</li>
</template>

<script>
'use strict';

module.exports = {
    replace: true,
    data: function() {
        return {
            placeholder: require('helpers/placeholders').user
        };
    }
};
</script>
