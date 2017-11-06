/**
 * Dataset display page JS module
 */
import FrontMixin from 'front/mixin';

import Vue from 'vue';
import config from 'config';
import log from 'logger';
import Velocity from 'velocity-animate';


// Components
import AddReuseModal from './add-reuse-modal.vue';
import DetailsModal from './details-modal.vue';
import ResourceModal from './resource-modal.vue';
import LeafletMap from 'components/leaflet-map.vue';
import FollowButton from 'components/buttons/follow.vue';
import FeaturedButton from 'components/buttons/featured.vue';
import ShareButton from 'components/buttons/share.vue';
import IntegrateButton from 'components/buttons/integrate.vue';
import IssuesButton from 'components/buttons/issues.vue';
import DiscussionThreads from 'components/discussions/threads.vue';


function parseUrl(url) {
    const a = document.createElement('a');
    a.href = url;
    return a;
}

new Vue({
    mixins: [FrontMixin],
    components: {
        LeafletMap, DiscussionThreads, FeaturedButton, IntegrateButton, IssuesButton, ShareButton, FollowButton
    },
    data() {
        return {
            dataset: this.extractDataset(),
            userReuses: []
        };
    },
    computed: {
        limitCheckDate() {
            const limitDate = new Date();
            limitDate.setSeconds(limitDate.getSeconds() - config.check_urls_cache_duration);
            return limitDate;
        }
    },
    ready() {
        this.loadCoverageMap();
        this.checkResources();
        this.fetchReuses();
        log.debug('Dataset display page ready');
    },
    methods: {
        /**
         * Extract the current dataset metadatas from JSON-LD script
         * @return {Object} The parsed dataset
         */
        extractDataset() {
            const selector = '#json_ld';
            const dataset = JSON.parse(document.querySelector(selector).text);
            dataset.resources = dataset.distribution;
            delete dataset.distribution;
            dataset.communityResources = dataset.contributedDistribution;
            delete dataset.contributedDistribution;
            dataset.keywords = dataset.keywords.split(',').map(keyword => keyword.trim());
            return dataset;
        },

        /**
         * Display a resource or a community ressource in a modal
         */
        showResource(id, e, isCommunity) {
            // Ensure edit button work
            if ([e.target, e.target.parentNode].some(el => el.classList.contains('btn-edit'))) return;
            e.preventDefault();
            const attr = isCommunity ? 'communityResources' : 'resources';
            const resource = this.dataset[attr].find(resource => resource['@id'] === id);
            this.$modal(ResourceModal, {resource});
        },

        /**
         * Expand the resource list and hide the expander
         */
        expandResources(e) {
            new Velocity(e.target, {height: 0, opacity: 0}, {complete(els) {
                els[0].remove();
            }});
            this.checkResourcesCollapsed();
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
         * The modal only show if there is candidate reuses
         */
        addReuse(e) {
            const reuses = this.userReuses.filter((reuse) => {
                // Exclude those already declaring this dataset
                return !reuse.datasets.some(dataset => dataset.id === this.dataset['@id']);
            });
            if (reuses.length) {
                e.preventDefault();
                this.$modal(AddReuseModal, {
                    dataset: this.dataset,
                    reuses: reuses,
                    formUrl: this.$els.addReuse.href,
                });
            }
        },

        /**
         * Fetch the current user reuses for display in add reuse modal
         */
        fetchReuses() {
            if (this.$user) {
                this.$api.get('me/reuses/').then(data => {
                    this.userReuses = data;
                });
            }
        },

        /**
         * Load coverage map data if required
         */
        loadCoverageMap() {
            if (!this.$refs.map) return;
            this.$api.get(this.$refs.map.$el.dataset.zones).then(data => {
                this.$refs.map.geojson = data;
            });
        },

        /**
         * Asynchronously check non-collapsed resources status
         */
        checkResources() {
            if (config.check_urls) {
                this.dataset.resources
                    .slice(0, config.dataset_max_resources_uncollapsed)
                    .forEach(this.checkResource);
            }
        },

        /**
         * Asynchronously check collapsed resources status
         */
        checkResourcesCollapsed() {
            if (config.check_urls) {
                this.dataset.resources
                    .slice(config.dataset_max_resources_uncollapsed)
                    .forEach(this.checkResource);
            }
        },

        /**
         * Get check related extras from JSON-LD
         * @param {Array} extras A list of extras in JSON-LD format
         * @return {Object} Check extras as a hash, if any
         */
        getCheckExtras(extras) {
            return extras.reduce((obj, extra) => {
                if (extra.name.startsWith('check:')) {
                    obj[extra.name] = extra.value;
                }
                return obj;
            }, {});
        },

        /**
         * Get a cached checked result from extras if fresh enough
         * @param  {Object} resource A resource as extracted from JSON-LD
         */
        getCachedCheck(resource) {
            const extras = this.getCheckExtras(resource.extras || []);
            if (extras['check:date']) {
                const checkDate = new Date(extras['check:date']);
                if (checkDate >= this.limitCheckDate) {
                    return extras;
                }
            }
        },

        /**
         * Get cached check or API check
         * @param  {Object} resource A resource element from DOM
         * @param  {String} checkurl The API check url
         */
        getResourceCheckStatus(resource_el, checkurl) {
            const cachedCheck = this.getCachedCheck(resource_el);
            return (cachedCheck && Promise.resolve(cachedCheck)) || this.$api.get(checkurl);
        },

        /**
         * Asynchronously check a displayed resource status
         * @param  {Object} resource A resource as extracted from JSON-LD
         */
        checkResource(resource) {
            const url = parseUrl(resource.contentUrl);
            const resource_el = document.querySelector(`#resource-${resource['@id']}`);
            const el = resource_el.querySelector('.format-label');
            const checkurl = resource_el.dataset.checkurl;
            if (url.protocol.startsWith('ftp')) {
                el.classList.add('format-label-warning');
                el.setTooltip(this._('The server may be hard to reach (FTP).'), true);
            } else {
                this.getResourceCheckStatus(resource, checkurl)
                .then((res) => {
                    const status = res['check:status'];
                    if (status >= 200 && status < 400) {
                        el.classList.add('format-label-success')
                    } else if (status >= 400 && status < 500) {
                        el.classList.add('format-label-danger');
                        el.setTooltip(this._('The resource cannot be found.'), true);
                    } else if (status >= 500) {
                        el.classList.add('format-label-warning');
                        el.setTooltip(this._('An error occured on the remote server. This may be temporary.'), true);
                    }
                })
                .catch(error => {
                    el.classList.add('format-label-unchecked');
                    console.log('Something went wrong with the linkchecker', error);
                });
            }
        },

        /**
         * Suggest a tag aka.trigger a new discussion
         */
        suggestTag() {
            this.$refs.discussions.start(
                this._('New tag suggestion to improve metadata'),
                this._('Hello,\n\nI propose this new tag: ')
            );
        }
    }
});
