<template>
<div class="card reuse-card">
    <a class="card-logo" :href="reuse.page">
        <img :alt="reuse.title" :src="reuse.image">
    </a>
    <div class="card-body">
        <h4>
            <a :href="reuse.page" :title="reuse.title">
                {{ reuse.title | truncate 100 }}
            </a>
        </h4>
    </div>
    <footer>
        <div class="author">
            <a class="avatar" :href="owner_url" :title="reuse.title">
            <img :src="owner_avatar" class="avatar" width="20" height="20"/>
            </a>
            <a class="user" :href="owner_url" :title="owner_name">
            {{ owner_name }}
            </a>
            <span class="date">{{ reuse.created_at | dt }}</span>
        </div>
    </footer>

    <a class="rollover fade in" :href="reuse.page"
        :title="reuse.title">
        {{{ reuse.description | markdown 120 }}}
    </a>
    <footer class="rollover fade in">
        <ul>
            <li>
                <a class="btn btn-xs" v-tooltip tooltip-placement="top" :title="_('Type')">
                    <span class="fa fa-file fa-fw"></span>
                    {{ reuse | reusetype }}
                </a>
            </li>
            <li>
                <a class="btn btn-xs" v-tooltip tooltip-placement="top"
                    :title="_('Number of datasets used')">
                    <span class="fa fa-cubes fa-fw"></span>
                    {{ reuse.datasets ? reuse.datasets.length : 0 }}
                </a>
            </li>

            <li>
                <a class="btn btn-xs" v-tooltip tooltip-placement="top" :title="_('Stars')">
                    <span class="fa fa-star fa-fw"></span>
                    {{ reuse.metrics ? reuse.metrics.followers || 0 : 0 }}
                </a>
            </li>
        </ul>
    </footer>
</div>
</template>

<script>
import Reuse from 'models/reuse';
import reuse_types from 'models/reuse_types';
import placeholders from 'helpers/placeholders';
import moment from 'moment';
import config from 'config';

const MASK = [
    'id',
    'title',
    'description',
    'image',
    'datasets{id}',
    'organization',
    'owner',
    'metrics',
    'page',
    'uri'
];

export default {
    MASK,
    props: {
        reuse: {
            type: Object,
            default: function() {return new Reuse();}
        },
        reuseid: null,
        reactive: {
            type: Boolean,
            default: true
        }
    },
    computed: {
        certified: function() {
            return `${config.theme_static}img/certified-stamp.png`;
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
    filters: {
        reusetype: function(reuse) {
            if (reuse && reuse.type) {
                return reuse_types.by_id(reuse.type).label;
            }
        }
    },
    methods: {
        fetch: function() {
            if (this.reuseid) {
                this.reuse.fetch(this.reuseid);
            }
        }
    },
    watch: {
        'reuseid': function(id) {
            this.fetch();
        }
    },
    ready: function() {
        this.fetch();
    }
};
</script>
