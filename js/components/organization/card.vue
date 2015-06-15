<template>
<div class="card organization-card"
    v-class="pointer: clickable, selected:selected" v-on="click: click">
    <a class="card-logo">
        <img alt="{{ organization.name }}" v-attr="src: logo">
    </a>
    <img v-if="organization.public_service"
        v-attr="src: certified_stamp" alt="certified"
        class="certified" rel="popover"
        data-title="{{ _('Certified public service') }}"
        data-content="{{ _('The identity of this public service public is certified by Etalab') }}"
        data-container="body" data-trigger="hover"/>
    <div class="card-body">
        <h4>
            <a title="{{organization.name}}">
                {{ organization.name | truncate 120 }}
            </a>
        </h4>
    </div>
    <footer>
        <ul>
            <li v-if="organization.metrics">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Datasets') }}">
                    <span class="fa fa-cubes fa-fw"></span>
                    {{ organization.metrics.datasets || 0 }}
                </a>
            </li>
            <li v-if="organization.metrics">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Reuses') }}">
                    <span class="fa fa-retweet fa-fw"></span>
                    {{ organization.metrics.reuses || 0 }}
                </a>
            </li>
            <li v-if="organization.metrics">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Followers') }}">
                    <span class="fa fa-star fa-fw"></span>
                    {{ organization.metrics.followers || 0 }}
                </a>
            </li>
        </ul>
    </footer>

    <a v-if="organization.description" class="rollover fade in"
        title="{{ organization.name }}">
        {{{ organization.description | markdown 180 }}}
    </a>
</div>
</template>

<script>
'use strict';

var Organization = require('models/organization'),
    placeholders = require('helpers/placeholders'),
    config = require('config');

module.exports = {
    data: function() {
        return {
            clickable: true,
            selected: false
        };
    },
    props: ['organization', 'orgid', 'clickable', 'selected'],
    computed: {
        logo: function() {
            if (!this.organization ||  !this.organization.logo) {
                return placeholders.organization;
            }
            return this.organization.logo;
        },
        certified_stamp: function() {
            return config.theme_static + 'img/certified-stamp.png';
        },
        spatial_label: function() {

        }
    },
    created: function() {
        if (!this.organization) {
            this.organization = new Organization();
        }
        if (this.orgid) {
            this.organization.fetch(this.orgid);
        }
    },
    methods: {
        click: function() {
            if (this.clickable) {
                this.$dispatch('organization:clicked', this.organization);
            }
        }
    }
};
</script>
