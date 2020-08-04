/**
 * Search display page JS module
 */
import 'less/front/search.less';

import FrontMixin from 'front/mixin';
import FacetsMixin from 'front/mixins/facets';

import log from 'logger';
import Vue from 'vue';


new Vue({
    mixins: [FrontMixin, FacetsMixin],
    ready() {
        log.debug('Search page');
    },
    methods: {
        /**
         * Change the current active tab
         * @param {String} id The tab identifier to display
         */
        setTab(id) {
            // Active tab
            [...document.querySelectorAll('.search-tabs li')].forEach(tab => {
                if (tab.dataset.tab === id) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            });
            // Active tab pane
            [...document.querySelectorAll('.tab-pane')].forEach(tabpane => {
                if (tabpane.id === id) {
                    tabpane.classList.add('active');
                } else {
                    tabpane.classList.remove('active');
                }
            });
            // Active toolbar
            [...document.querySelectorAll('.btn-toolbar.wrapper')].forEach(toolbar => {
                if (toolbar.dataset.tab === id) {
                    toolbar.classList.remove('hide');
                } else {
                    toolbar.classList.add('hide');
                }
            });
        },
    }
});
