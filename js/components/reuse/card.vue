<style lang="less"></style>

<template>
<div class="card reuse-card">
    <a class="card-logo" href="{{ reuse.page }}">
        <img alt="{{ reuse.title }}" v-attr="src: reuse.image">
    </a>
    <div class="card-body">
        <h4>
            <a href="{{ reuse.page }}" title="{{reuse.title}}">
                {{ reuse.title | truncate 100 }}
            </a>
        </h4>
    </div>
    <footer>
        <div class="author">
            <a class="avatar" href="{{owner_url}}" title="{{reuse.title}}">
            <img v-attr="src: owner_avatar" class="avatar" width="20" height="20"/>
            </a>
            <a class="user" href="{{ owner_url }}" title="{{ owner_name }}">
            {{ owner_name }}
            </a>
            <span class="date">{{ reuse.created_at | dt }}</span>
        </div>
    </footer>

    <a class="rollover fade in" href="{{ reuse.page }}"
        title="{{ reuse.title }}">
        {{{ reuse.description | markdown 120 }}}
    </a>
    <footer class="rollover fade in">
        <ul>
            <li>
                <a class="btn btn-xs" rel="tooltip" data-placement="top"
                    title="{{ _('Type') }}">
                    <span class="fa fa-file fa-fw"></span>
                    {{ reuse.type }}
                </a>
            </li>
            <li>
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Number of datasets used') }}">
                    <span class="fa fa-cubes fa-fw"></span>
                    {{ reuse.datasets ? reuse.datasets.length : 0 }}
                </a>
            </li>

            <li>
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Stars') }}">
                    <span class="fa fa-star fa-fw"></span>
                    {{ reuse.metrics ? reuse.metrics.followers || 0 : 0 }}
                </a>
            </li>
        </ul>
    </footer>
</div>
</template>

<script>
'use strict';

var Reuse = require('models/reuse'),
    placeholders = require('helpers/placeholders'),
    moment = require('moment'),
    config = require('config');

module.exports = {
    paramAttributes: ['reuse', 'reuseid'],
    data: function() {
        return {
            reuse: new Reuse(),
            reuseid: null,
            reactive: true
        };
    },
    computed: {
        certified: function() {
            return config.theme_static + 'img/certified-stamp.png';
        },
        spatial_label: function() {

        },
        owner_avatar: function() {
            if (this.reuse.organization) {
                return this.reuse.organization.logo || placeholders.organization;
            } else if (this.reuse.owner) {
                return this.reuse.owner.avatar || placeholders.user;
            }
        },
        owner_url: function() {
            if (this.reuse.organization) {
                return this.reuse.organization.page;
            } else if (this.reuse.owner) {
                return this.reuse.owner.page
            }
        },
        owner_name: function() {
            if (this.reuse.organization) {
                return this.reuse.organization.name;
            } else if (this.reuse.owner) {
                return this.reuse.owner.first_name + ' ' + this.reuse.owner.last_name;
            }
        }
    },
    // created: function() {
    //     if (!this.reuse && this.reuseid) {
    //         this.reuse = new Reuse().fetch(this.reuseid);
    //     }
    // },
    watch: {
        'reuseid': function(id) {
            if (id) {
                this.reuse.fetch(id);
            }
        }
    }
};
</script>
