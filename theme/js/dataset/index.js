/**
 * Dataset display page JS module
 */
import 'less/front/dataset.less';

import FrontMixin from 'front/mixin';

import Vue from 'vue';
import config from 'config';
import log from 'logger';
import Velocity from 'velocity-animate';


// Components
import AddReuseModal from './add-reuse-modal.vue';
import DetailsModal from './details-modal.vue';
import PreviewModal from './preview-modal.vue';
import ResourceModal from './resource-modal.vue';
import Availability from './resource/availability.vue';
import LeafletMap from 'components/leaflet-map.vue';
import FollowButton from 'components/buttons/follow.vue';
import FeaturedButton from 'components/buttons/featured.vue';
import ShareButton from 'components/buttons/share.vue';
import IntegrateButton from 'components/buttons/integrate.vue';
import IssuesButton from 'components/buttons/issues.vue';
import DiscussionThreads from 'components/discussions/threads.vue';


const RESOURCE_REGEX = /^#resource(-community)?-([0-9a-f-]{36})$/;

new Vue({
    mixins: [FrontMixin],
    components: {
        LeafletMap, DiscussionThreads, FeaturedButton, IntegrateButton, IssuesButton,
        ShareButton, FollowButton, Availability, PreviewModal,
    },
    data() {
        return {
            dataset: this.extractDataset(),
            userReuses: [],
            visibleTypeLists: [],
        };
    },
    ready() {
        this.loadCoverageMap();
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
         * Is a resource type list collapsed
         * @type {String}
         * @return {Boolean}
         */
        isTypeListVisible(type) {
            return this.visibleTypeLists.indexOf(type) !== -1;
        },

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
         * Get a resource object conform to model (but not a Model instance) from JSON-LD
         * @param  {Object} resourceJsonLd  Resource as in JSON-LD
         * @return {Object}                 Resource object as it would be in model
         */
        resourceFromJsonLd(resourceJsonLd) {
            const resource = {
                id: resourceJsonLd['@id'],
                url: resourceJsonLd.contentUrl,
                latest: resourceJsonLd.url,
                title: resourceJsonLd.name,
                format: resourceJsonLd.encodingFormat,
                mime: resourceJsonLd.fileFormat,
                filesize: resourceJsonLd.contentSize,
                created_at: resourceJsonLd.dateCreated,
                modified: resourceJsonLd.dateModified,
                published: resourceJsonLd.datePublished,
                description: resourceJsonLd.description,
                type: resourceJsonLd.type,
            };
            if (resourceJsonLd.interactionStatistic) {
                resource.metrics = {
                    views: resourceJsonLd.interactionStatistic.userInteractionCount,
                }
            }
            resource.extras = {};
            return resource;
        },

        /**
         * Display a resource or a community ressource in a modal
         */
        showResource(id, isCommunity) {
            const attr = isCommunity ? 'communityResources' : 'resources';
            const resourceJsonLd = this.dataset[attr].find(resource => resource['@id'] === id);
            const communityPrefix = isCommunity ? '-community' : '';
            location.hash = `resource${communityPrefix}-${id}`;
            const modal = this.$modal(
                ResourceModal,
                {
                    datasetId: this.dataset['@id'],
                    resource: this.resourceFromJsonLd(resourceJsonLd),
                    isCommunity: isCommunity,
                }
            );
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
            this.visibleTypeLists.push(type);
        },

        /**
         * Display the details modal
         */
        showDetails() {
            this.$modal(DetailsModal, {dataset: this.dataset});
        },

        /**
         * Display a preview URL
         */
        showPreview(url) {
            this.$modal(PreviewModal, {url});
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
                this.showResource(id, !!isCommunity);
            }
        },

        /**
         * Get resource by id from dataset JSON-LD
         */
        getResourceById(resourceId) {
            return this.dataset.resources.find(r => r['@id'] === resourceId);
        },

        /**
         * Is check enabled for a particular resourceType (and globally)
         */
        isCheckEnabled(resourceType) {
            if (!config.check_urls) return false;
            return config.unchecked_types.indexOf(resourceType) == -1;
        },
    }
});
