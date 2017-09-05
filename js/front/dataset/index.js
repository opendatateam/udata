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
        const data = {
            dataset: this.extractDataset(),
            userReuses: []
        };
        return data;
    },
    ready() {
        this.loadCoverageMap();
        this.fetchReuses();
        log.debug('Dataset display page ready');
        // TODO better coupling strategy
        window.addEventListener('load', () => {
            if (linkchecker) {
                this.checkResources();
            }
        })
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
         * Asynchronously check all resources status
         */
        checkResources() {
            this.dataset.resources.forEach(this.checkResource);
        },

        /**
         * Asynchronously check a displayed resource status
         * @param  {Object} resource A resource as extracted from JSON-LD
         */
        checkResource(resource) {
            const url = parseUrl(resource.contentUrl);
            const resource_el = document.querySelector(`#resource-${resource['@id']}`);
            const group = this.dataset.alternateName;
            linkchecker.checkUrl(url, group, resource_el);
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
