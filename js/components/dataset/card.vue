<template>
<a class="card dataset-card" :class="{ selected: selected }" :title="dataset.full_title"
    :href="clickable" @click.prevent="click">
    <div v-if="dataset.organization" class="card-logo">
        <img :alt="dataset.organization.name" :src="logo">
    </div>

    <img v-if="dataset.organization && dataset.organization.public_service"
        :src="certified" alt="certified" class="certified"
        v-popover="_('The identity of this public service is certified by %(certifier)s', certifier=config.SITE_AUTHOR)"
        :popover-title="_('Certified public service')"
        popover-trigger="hover"/>

    <div class="card-body">
        <h4>{{ dataset.full_title | truncate 80 }}</h4>
        <div class="clamp-3">{{{ dataset.description | markdown 180 }}}</div>
    </div>

    <footer class="card-footer">
        <ul>
            <li v-tooltip :title="_('Resources count')">
                <span class="fa fa-files-o fa-fw"></span>
                {{ dataset.resources.length  }}
            </li>
            <li v-if="dataset.spatial && dataset.spatial.zones && dataset.spatial.zones.length > 0" v-tooltip
                :title="_('Territorial coverage')">
                <span class="fa fa-map-marker fa-fw"></span>
                {{ dataset.spatial.zones[0].name }}
            </li>
            <li v-if="dataset.metrics" v-tooltip :title="_('Reuses')">
                <span class="fa fa-recycle fa-fw"></span>
                {{ dataset.metrics.reuses || 0 }}
            </li>
            <li v-if="dataset.metrics" v-tooltip :title="_('Stars')">
                <span class="fa fa-star fa-fw"></span>
                {{ dataset.metrics.followers || 0 }}
            </li>

            <!-- Temporal coverage -->
            <li v-if="dataset.temporal_coverage" v-tooltip :title="_('Temporal coverage')">
                <span class="fa fa-calendar fa-fw"></span>
                {{ dataset.temporal_coverage | daterange }}
            </li>

            <!-- Territorial coverage -->
            <li v-if="dataset.spatial && dataset.spatial.granularity" v-tooltip :title="_('Territorial coverage granularity')">
                <span class="fa fa-bullseye fa-fw"></span>
                {{ dataset | granularity_label }}
            </li>
        </ul>

    </footer>
</a>
</template>

<script>
import Dataset from 'models/dataset';
import DatasetFilters from 'components/dataset/filters';
import placeholders from 'helpers/placeholders';
import config from 'config';

const MASK = [
    'id', 'title', 'acronym', 'description', 'metrics', 'organization',
    'spatial{zones,granularity}', 'frequency', 'temporal_coverage',
    'page', 'uri'
];

export default {
    MASK,
    mixins: [DatasetFilters],
    props: {
        dataset: {
            type: Object,
            default: () => new Dataset({mask: MASK})
        },
        datasetid: null,
        clickable: {
            type: Boolean,
            default: false
        },
        selected: {
            type: Boolean,
            default: false
        }
    },
    computed: {
        logo() {
            if (!this.dataset || !this.dataset.organization
                || !this.dataset.organization.logo_thumbnail && !this.dataset.organization.logo) {
                return placeholders.organization;
            }
            return this.dataset.organization.logo_thumbnail || this.dataset.organization.logo;
        },
        certified() {
            return `${config.theme_static}img/certified-stamp.png`;
        },
        spatial_label() {

        }
    },
    methods: {
        fetch() {
            if (this.datasetid) {
                this.dataset.fetch(this.datasetid);
            }
        },
        click() {
            if (this.clickable) {
                this.$dispatch('dataset:clicked', this.dataset);
            }
        }
    },
    watch: {
        datasetid(id) {
            this.fetch();
        }
    },
    ready() {
        this.fetch();
    }
};
</script>
