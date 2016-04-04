/**
 * Dataset display page JS module
 */
// Catch all errors
import 'raven';

// ES6 environment
import 'babel-polyfill';

import $ from 'jquery'; // Only needed for tooltips :(

import Auth from 'auth';
import Vue from 'vue';
import config from 'config';
import log from 'logger';
import microdata from 'microdata';
import utils from 'utils';
import Velocity from 'velocity-animate';

// Components
import AddReuseModal from './add-reuse-modal.vue';
import DetailsModal from './details-modal.vue';
import ResourceModal from './resource-modal.vue';
import LeafletMap from 'components/leaflet-map.vue';

// Legacy widgets
import 'widgets/featured';
import 'widgets/follow-btn';
import 'widgets/issues-btn';
import 'widgets/discussions-btn';
import 'widgets/share-btn';
import 'widgets/integrate-btn';

Vue.config.debug = config.debug;

Vue.use(require('plugins/api'));
Vue.use(require('plugins/text'));
Vue.use(require('plugins/i18next'));


function parseUrl(url) {
    const a = document.createElement('a');
    a.href = url;
    return a;
}


function addTooltip(el, content) {
    el.setAttribute('rel', 'tooltip');
    el.setAttribute('data-original-title', content);
    el.dataset.placement = 'left';
    $(el).tooltip('show');  // Only jQuery requirement left
}


new Vue({
    el: 'body',
    components: {LeafletMap},
    data() {
        const data = {
            dataset: this.extractDataset(),
            userReuses: [],
        };
        if (config.check_urls) {
            const port = location.port ? `:${location.port}` : '';
            const domain = `${location.hostname}${port}`;
            data.whitelist = [domain].concat(config.check_urls_whitelist || []);
        }
        return data;
    },
    ready() {
        this.loadCoverageMap();
        this.checkResources();
        this.fetchReuses();
        log.debug('Dataset display page ready');
    },
    methods: {
        /**
         * Insert a modal Vue in the application.
         * @param  {Object} options     The modal component definition (options passed to Vue.extend())
         * @param  {Object} data        Data to assign to modal properties
         * @return {Vue}                The child instanciated vm
         */
        $modal(options, data) {
            const constructor = Vue.extend(options);
            return new constructor({
                el: this.$els.modal,
                replace: false, // Needed while all components are not migrated to replace: true behavior
                parent: this,
                data: data
            });
        },

        /**
         * Extract the current dataset metadatas from microdata markup
         * @return {Object} The parsed dataset
         */
        extractDataset() {
            const dataset = microdata('http://schema.org/Dataset')[0];
            if (Array.isArray(dataset.distribution)) {
                dataset.resources = dataset.distribution;
            } else {
                dataset.resources = dataset.distribution ? [dataset.distribution] : [];
            }
            delete dataset.distribution;
            if (utils.isString(dataset.keywords)) {
                dataset.keywords = [dataset.keywords];
            }
            dataset.extras = microdata('http://schema.org/PropertyValue');
            return dataset;
        },

        /**
         * Display a resource in a modal
         */
        showResource(id, e) {
            // Ensure edit button work
            if ([e.target, e.target.parentNode].some((el) => {el.classList.contains('btn-edit');})) {
                return;
            }
            const resource = this.dataset.resources.filter(resource => resource.id === id)[0];
            this.$modal(ResourceModal, {resource: resource});
            e.preventDefault();
        },

        /**
         * Expand the resource list and hide the expander
         */
        expandResources(e) {
            new Velocity(e.target, {height: 0, opacity: 0}, {complete(els) {
                els[0].remove();
            }});
        },

        /**
         * Display the details modal
         */
        showDetails() {
            this.$modal(DetailsModal, {dataset: this.dataset});
        },

        /**
         * Display a modal with the user reuses
         * allowing him to chose an existing.
         *
         * The modal only show ff there is candidate reuses
         */
        addReuse(e) {
            const reuses = this.userReuses.filter((reuse) => {
                // Exclude those already declaring this dataset
                return !reuse.datasets.some(dataset => dataset.id === this.dataset.id);
            });
            if (reuses.length) {
                this.$modal(AddReuseModal, {
                    dataset: this.dataset,
                    reuses: reuses,
                    formUrl: this.$els.addReuse.href,
                });
                e.preventDefault();
            }
        },

        /**
         * Fetch the current user reuses for display in add reuse modal
         */
        fetchReuses() {
            if (Auth.user) {
                this.$http.get('me/reuses/').then(response => {
                    this.userReuses = response.data;
                });
            }
        },

        /**
         * Load coverage map data if required
         */
        loadCoverageMap() {
            if (!this.$refs.map) return;
            this.$http.get(this.$refs.map.$el.dataset.zones).then(response => {
                this.$refs.map.geojson = response.data;
            });
        },

        /**
         * Asynchronuously check all resources status
         */
        checkResources() {
            if (config.check_urls) {
                this.dataset.resources.forEach(resource => this.checkResource(resource));
            }
        },

        /**
         * Asynchronuously check a displayed resource status
         * @param  {Object} resource A resource as extracted from microdata
         */
        checkResource(resource) {
            const url = parseUrl(resource.url);
            const el = resource.$el.querySelector('.format-label');
            const checkurl = resource.$el.dataset.checkurl;
            if (!this.whitelist.some(domain => url.origin.endsWith(domain))) {
                if (url.protocol.startsWith('ftp')) {
                    el.classList.add('format-label-warning');
                    addTooltip(el, this._('The server may be hard to reach (FTP).'));
                } else {
                    this.$http.get(checkurl, {url: url.href, group: this.dataset.alternateName})
                    .then(response => {
                        if (response.status === 200) {
                            el.classList.add('format-label-success');
                        } else if (response.status === 404) {
                            el.classList.add('format-label-warning');
                            addTooltip(el, this._('The resource cannot be found.'));
                        }
                    }, response => {
                        if (response.status !== 503) {
                            el.classList.add('format-label-danger');
                            addTooltip(el, this._('The server cannot be found.'));
                        }
                    });
                }
            }
        }
    }
});
