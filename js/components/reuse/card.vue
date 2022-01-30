<template>
<a class="card reuse-card" :class="{ 'selected': selected }" :title="reuse.title"
    :href="clickable" @click.prevent="click">
    <div class="card-logo">
        <img :alt="reuse.title" :src="reuse.image">
    </div>
    <div class="card-body">
        <h4>{{ reuse.title | truncate 100 }}</h4>
        <div class="clamp-3">{{{ reuse.description | markdown 120 }}}</div>
    </div>

    <footer class="card-footer">
        <ul>
            <li v-tooltip :title="_('Type')">
                <span class="fa fa-file fa-fw"></span>
                {{ reuse | reusetype }}
            </li>
            <li v-tooltip :title="_('Topic')">
                <span class="fa fa-file fa-fw"></span>
                {{ reuse | reusetopic }}
            </li>
            <li v-tooltip :title="_('Number of datasets used')">
                <span class="fa fa-cubes fa-fw"></span>
                {{ reuse.datasets ? reuse.datasets.length : 0 }}
            </li>

            <li v-tooltip :title="_('Stars')">
                <span class="fa fa-star fa-fw"></span>
                {{ reuse.metrics ? reuse.metrics.followers || 0 : 0 }}
            </li>
        </ul>
    </footer>
</a>
</template>

<script>
import Reuse from 'models/reuse';
import reuse_types from 'models/reuse_types';
import reuse_topics from 'models/reuse_topics';
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
            default: () => new Reuse({mask: MASK})
        },
        reuseid: null,
        clickable: {
            type: Boolean,
            default: true
        },
        selected: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        certified() {
            return `${config.theme_static}img/certified-stamp.png`;
        },
        owner_avatar() {
            if (this.reuse.organization) {
                return this.reuse.organization.logo || placeholders.organization;
            } else if (this.reuse.owner) {
                return this.reuse.owner.avatar || placeholders.user;
            }
        },
        owner_url() {
            if (this.reuse.organization) {
                return this.reuse.organization.page;
            } else if (this.reuse.owner) {
                return this.reuse.owner.page
            }
        },
        owner_name() {
            if (this.reuse.organization) {
                return this.reuse.organization.name;
            } else if (this.reuse.owner) {
                return `${this.reuse.owner.first_name} ${this.reuse.owner.last_name}`;
            }
        }
    },
    filters: {
        reusetype(reuse) {
            if (reuse && reuse.type) {
                return reuse_types.by_id(reuse.type).label;
            }
        },
        reusetopic(reuse) {
            if (reuse && reuse.topic) {
                return reuse_topics.by_id(reuse.topic).label;
            }
        }
    },
    methods: {
        fetch() {
            if (this.reuseid) {
                this.reuse.fetch(this.reuseid);
            }
        },
        click() {
            if (this.clickable) {
                this.$dispatch('reuse:clicked', this.reuse);
            }
        }
    },
    watch: {
        reuseid(id) {
            this.fetch();
        }
    },
    ready() {
        this.fetch();
    }
};
</script>
