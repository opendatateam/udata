<style lang="less">
.row.user-card-filter-search {
    margin-bottom: 20px;
}
</style>

<template>
<div class="row user-card-filter-search">
    <div class="col-xs-12 col-md-6 col-md-offset-3">
        <form class="search-form">
            <div class="input-group">
                <input type="text" name="search" class="form-control"
                    placeholder="{{ _('Search') }}" v-model="search_query">
                <div class="input-group-btn">
                    <button type="submit" name="submit" class="btn btn-warning btn-flat">
                        <span class="fa fa-search"></span>
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>
<div class="row user-card-filter-cardlist" v-if="completions">
    <user-card class="{{cardclass}}"
        v-repeat="user:users"
        >
    </user-card>
</div>
<div class="row" v-if="!search_query">
    <p class="col-xs-12 lead text-center">
        {{ _('Start typing to find your user.') }}
    </p>
</div>
<div class="row" v-if="search_query && !users.length">
    <p class="col-xs-12 lead text-center">
        {{ _('No user found.') }}
    </p>
</div>
</template>

<script>
'use strict';

var API = require('api'),
    log = require('logger'),
    User = require('models/user');

module.exports = {
    components: {
        'user-card': require('components/user/card.vue')
    },
    data: function() {
        return {
            search_query: '',
            cardclass: 'col-xs-12 col-md-4 col-lg-3',
            completions: []
        };
    },
    paramAttributes: ['cardclass'],
    computed: {
        users: function() {
            return this.completions.map(function(user) {
                return new User({data: {
                    id: user.id,
                    avatar: user.avatar_url,
                    fullname: user.fullname,
                    page: '/user/' + user.slug + '/'
                }});
            });
        }
    },
    watch: {
        search_query: function(query) {
            API.users.suggest_users({
                q: query,
                size: 9
            }, function(data) {
                this.completions = data.obj;
            }.bind(this), function(message) {
                log.error('Unable to fetch users', message);
            });
        }
    }
};
</script>
