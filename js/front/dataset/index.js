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
import AvailabilityFromStatus from './resource/availability-from-status.vue';
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

const RESOURCE_REGEX = /^#resource(-community)?-([0-9a-f-]{36})$/;

new Vue({
    mixins: [FrontMixin],
    components: {
        LeafletMap, DiscussionThreads, FeaturedButton, IntegrateButton, IssuesButton,
        ShareButton, FollowButton, AvailabilityFromStatus,
    },
    data() {
        return {
            dataset: this.extractDataset(),
            userReuses: [],
            checkResults: [],
        };
    },
    ready() {
        this.loadCoverageMap();
        this.checkResources();
        this.fetchReuses();
        if (document.location.hash) {
            this.$nextTick(() => { // Wait for data to be binded
                this.openResourceFromHash(document.location.hash);
            });
        }
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
        showResource(id, isCommunity) {
            const attr = isCommunity ? 'communityResources' : 'resources';
            const resource = this.dataset[attr].find(resource => resource['@id'] === id);
            const communityPrefix = isCommunity ? '-community' : '';
            location.hash = `resource${communityPrefix}-${id}`;
            const modal = this.$modal(ResourceModal, {resource});
            modal.$on('modal:closed', () => {
                // prevent scrolling to top
                location.hash = '_';
            });
        },

        /**
         * Expand the resource list and hide the expander
         */
        expandResources(e, type) {
            new Velocity(e.target, {height: 0, opacity: 0}, {complete(els) {
                els[0].remove();
            }});
            this.checkResourcesCollapsed(type);
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
                const types = this.dataset.resources
                    .map(r => r.type)
                    .filter((v, i, a) => a.indexOf(v) === i);
                types.forEach(type => {
                    this.dataset.resources
                        .filter(r => r.type == type)
                        .slice(0, config.dataset_max_resources_uncollapsed)
                        .forEach(this.checkResource);
                });
            }
        },

        /**
         * Asynchronously check collapsed resources status
         */
        checkResourcesCollapsed(type) {
            if (config.check_urls) {
                this.dataset.resources
                    .filter(r => r.type == type)
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
         * Get a cached checked result from extras if resource is not flagged
         * as needing a new check
         * @param  {Object} resource A resource as extracted from JSON-LD
         */
        getCachedCheck(resource) {
            if (!resource.needCheck) {
                const extras = this.getCheckExtras(resource.extras || []);
                if (extras['check:status']) {
                    return extras
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
            const el = resource_el.querySelector('.healthcheck-container');
            const checkurl = resource_el.dataset.checkurl;
            this.getResourceCheckStatus(resource, checkurl)
                .then((res) => {
                    this.checkResults.push({
                        id: resource['@id'],
                        status: res['check:status']
                    });
                })
                .catch(error => {
                    console.log('Something went wrong with the linkchecker', error);
                });
        },

        /**
         * Suggest a tag aka.trigger a new discussion
         */
        suggestTag() {
            this.$refs.discussions.start(
                this._('New tag suggestion to improve metadata'),
                this._('Hello,\n\nI propose this new tag: ')
            );
        },

        /**
         * Open resource modal if corresponding hash in URL.
         * /!\ there is a similar function in <discussion-threads> (jumpToHash),
         * jump may come from there too.
         */
        openResourceFromHash(hash) {
            if (RESOURCE_REGEX.test(hash)) {
                const [, isCommunity, id] = hash.match(RESOURCE_REGEX);
                this.showResource(id, isCommunity);
            }
        },

        /**
         * Return currently computed check result for resourceId
         */
        checkResultFor(resourceId) {
            return this.checkResults.find((res) => {
                return res.id == resourceId;
            })
        },
    }
});
