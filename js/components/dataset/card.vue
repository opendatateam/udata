<template>
<div class="card dataset-card">
    <a v-if="dataset.organization" class="card-logo" href="{{ dataset.page }}">
        <img alt="{{ dataset.organization.name }}" :src="logo">
    </a>
    <img v-if="dataset.organization && dataset.organization.public_service"
        :src="certified" alt="certified"
        class="certified" rel="popover"
        data-title="{{ _('Certified public service') }}"
        data-content="{{ _('The identity of this public service public is certified by Etalab') }}"
        data-container="body" data-trigger="hover"/>
    <div class="card-body">
        <h4>
            <a href="{{ dataset.page }}" title="{{dataset.title}}">
                {{ dataset.title | truncate 80 }}
            </a>
        </h4>
    </div>
    <footer>
        <ul>
            <li v-if="dataset.spatial && dataset.spatial.territories && dataset.spatial.territories.length > 0">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Territorial coverage') }}">
                    <span class="fa fa-map-marker fa-fw"></span>
                    {{ dataset.spatial.territories[0].name }}
                </a>
            </li>
            <li v-if="dataset.metrics">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Reuses') }}">
                    <span class="fa fa-retweet fa-fw"></span>
                    {{ dataset.metrics.reuses || 0 }}
                </a>
            </li>
            <li v-if="dataset.metrics">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Stars') }}">
                    <span class="fa fa-star fa-fw"></span>
                    {{ dataset.metrics.followers || 0 }}
                </a>
            </li>
        </ul>
    </footer>

    <a class="rollover fade in" href="{{ dataset.page }}"
        title="{{ dataset.title }}">
        {{{ dataset.description | markdown 180 }}}
    </a>
    <footer class="rollover fade in">
        <ul>
            <!-- Temporal coverage -->
            <li v-if="dataset.temporal_coverage">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Temporal coverage') }}">
                    <span class="fa fa-calendar fa-fw"></span>
                    {{ dataset.temporal_coverage | daterange }}
                </a>
            </li>

            <!-- Territorial coverage -->
            <li v-if="dataset.spatial && dataset.spatial.granularity">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Territorial coverage granularity') }}">
                    <span class="fa fa-bullseye fa-fw"></span>
                    {{ dataset | granularity_label }}
                </a>
            </li>

            <!-- frequency -->
            <li v-if="dataset.frequency">
                <a class="btn btn-xs" rel="tooltip"
                    data-placement="top" data-container="body"
                    title="{{ _('Frequency') }}">
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
import placeholders from 'helpers/placeholders';
import moment from 'moment';
import config from 'config';
import granularities from 'models/geogranularities';
import frequencies from 'models/frequencies';

export default {
    data: function() {
        return {
            dataset: new Dataset(),
            datasetid: null,
            reactive: true
        };
    },
    props: ['dataset', 'datasetid', 'reactive'],
    computed: {
        logo: function() {
            if (!this.dataset || !this.dataset.organization || !this.dataset.organization.logo) {
                return placeholders.organization;
            }
            return this.dataset.organization.logo;
        },
        certified: function() {
            return config.theme_static + 'img/certified-stamp.png';
        },
        spatial_label: function() {

        }
    },
    filters: {
        /**
         * Display a date range in the shorter possible maner.
         */
        daterange: function(range) {
            if (!range || !range.start) {
                return;
            }
            var start = moment(range.start),
                end = range.end ? moment(range.end) : undefined,
                start_label, end_label;

            start_label = start.format('L');
            end_label = end.format('L');
            // delta = start.diff(end)
            // delta = value.end - value.start
            // start, end = None, None
            // if start.clone() is_first_year_day(value.start) and is_last_year_day(value.end):
            //     start = value.start.year
            //     if delta.days > 365:
            //         end = value.end.year
            // elif is_first_month_day(value.start) and is_last_month_day(value.end):
            //     start = short_month(value.start)
            //     if delta.days > 31:
            //         end = short_month(value.end)
            // else:
            //     start = short_day(value.start)
            //     if value.start != value.end:
            //         end = short_day(value.end)
            return end_label
                ? this._('{start} to {end}', {start:start_label, end:end_label})
                : start_label;
        },
        frequency_label: function(dataset) {
            if (dataset && dataset.frequency) {
                return frequencies.by_id(dataset.frequency).label;
            }
        },
        granularity_label: function(dataset) {
            if (dataset && dataset.spatial && dataset.spatial.granularity) {
                return granularities.by_id(dataset.spatial.granularity).name;
            }
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
