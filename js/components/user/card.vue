<template>
<div class="card user-card"
    :class="{ 'pointer': clickable, 'selected': selected }" @click="click">
    <a class="card-logo">
        <img alt="{{ user | display }}" :src="avatar">
    </a>
    <div class="card-body">
        <h4>
            <a title="{{ user | display }}">
                {{ user | display }}
            </a>
        </h4>
    </div>
    <footer v-if="user.metrics">
        <ul>
            <li>
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Datasets') }}">
                    <span class="fa fa-cubes fa-fw"></span>
                    {{ user.metrics.datasets || 0 }}
                </a>
            </li>
            <li>
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Reuses') }}">
                    <span class="fa fa-retweet fa-fw"></span>
                    {{ user.metrics.reuses || 0 }}
                </a>
            </li>
            <li>
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Followers') }}">
                    <span class="fa fa-star fa-fw"></span>
                    {{ user.metrics.followers || 0 }}
                </a>
            </li>
        </ul>
    </footer>

    <a v-if="user.about" class="rollover fade in"
        title="{{ user | display }}">
        {{{ user.about | markdown 180 }}}
    </a>
</div>
</template>

<script>
'use strict';

var User = require('models/user'),
    placeholders = require('helpers/placeholders');

module.exports = {
    data: function() {
        return {
            clickable: true,
            selected: false
        };
    },
    props: ['user', 'userid', 'selected'],
    computed: {
        avatar: function() {
            if (!this.user || !this.user.avatar) {
                return placeholders.user;
            }
            return this.user.avatar;
        }
    },
    created: function() {
        if (!this.user) {
            this.user = new User();
        }
        if (this.userid) {
            this.user.fetch(this.userid);
        }
    },
    methods: {
        click: function() {
            if (this.clickable) {
                this.$dispatch('user:clicked', this.user);
            }
        }
    }
};
</script>
