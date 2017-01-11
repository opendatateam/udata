<template>
<div class="card dataset-card">
    <a v-if="dataset.organization" class="card-logo" :href="dataset.page">
        <img :alt="dataset.organization.name" :src="logo">
    </a>
    <img v-if="dataset.organization && dataset.organization.public_service"
        :src="certified" alt="certified"
        class="certified" data-toggle="popover"
        :data-title="_('Certified public service')"
        :data-content="_('The identity of this public service is certified by %(certifier)s', certifier=config.SITE_AUTHOR)"
        data-container="body" data-trigger="hover"/>
    <div class="card-body">
        <h4>
            <a :href="dataset.page" :title="dataset.title">
                {{ dataset.title | truncate 80 }}
            </a>
        </h4>
    </div>
    <footer>
        <ul>
            <li v-if="dataset.spatial && dataset.spatial.zones && dataset.spatial.zones.length > 0">
                <a class="btn btn-xs" v-tooltip tooltip-placement="top" :title="_('Territorial coverage')">
                    <span class="fa fa-map-marker fa-fw"></span>
                    {{ dataset.spatial.zones[0].name }}
                </a>
            </li>
            <li v-if="dataset.metrics">
                <a class="btn btn-xs" v-tooltip tooltip-placement="top" :title="_('Reuses')">
                    <span class="fa fa-retweet fa-fw"></span>
                    {{ dataset.metrics.reuses || 0 }}
                </a>
            </li>
            <li v-if="dataset.metrics">
                <a class="btn btn-xs" v-tooltip tooltip-placement="top" :title="_('Stars')">
                    <span class="fa fa-star fa-fw"></span>
                    {{ dataset.metrics.followers || 0 }}
                </a>
            </li>
        </ul>
    </footer>

    <a class="rollover fade in" :href="dataset.page"
        :title="dataset.title">
        {{{ dataset.description | markdown 180 }}}
    </a>
    <footer class="rollover fade in">
        <ul>
            <!-- Temporal coverage -->
            <li v-if="dataset.temporal_coverage">
                <a class="btn btn-xs" v-tooltip tooltip-placement="top" :title="_('Temporal coverage')">
                    <span class="fa fa-calendar fa-fw"></span>
                    {{ dataset.temporal_coverage | daterange }}
                </a>
            </li>

            <!-- Territorial coverage -->
            <li v-if="dataset.spatial && dataset.spatial.granularity">
                <a class="btn btn-xs" v-tooltip tooltip-placement="top"
                    :title="_('Territorial coverage granularity')">
                    <span class="fa fa-bullseye fa-fw"></span>
                    {{ dataset | granularity_label }}
                </a>
            </li>

            <!-- frequency -->
            <li v-if="dataset.frequency">
                <a class="btn btn-xs" v-tooltip tooltip-placement="top" :title="_('Frequency')">
                    <span class="fa fa-clock-o fa-fw"></span>
                    {{ dataset | frequency_label }}
                </a>
            </li>
        </ul>

    </footer>
</div>
</template>

<script>
import Dataset from 'models/dataset';
import DatasetFilters from 'components/dataset/filters';
import placeholders from 'helpers/placeholders';
import config from 'config';

const MASK = [
    'id', 'title', 'description', 'metrics', 'organization',
    'spatial{zones,granularity}', 'frequency', 'temporal_coverage',
    'page', 'uri'
];

export default {
    MASK,
    mixins: [DatasetFilters],
    props: {
        dataset: {
            type: Object,
            default: function() {return new Dataset({mask: MASK});}
        },
        datasetid: null,
        reactive: {
            type: Boolean,
            default: true
        }
    },
    computed: {
        logo: function() {
            if (!this.dataset || !this.dataset.organization || !this.dataset.organization.logo) {
                return placeholders.organization;
            }
            return this.dataset.organization.logo;
        },
        certified: function() {
            return `${config.theme_static}img/certified-stamp.png`;
        },
        spatial_label: function() {

        }
    },
    methods: {
        fetch: function() {
            if (this.datasetid) {
                this.dataset.fetch(this.datasetid);
            }
        }
    },
    watch: {
        datasetid: function(id) {
            this.fetch();
        }
    },
    ready: function() {
        this.fetch();
    }
};
</script>
