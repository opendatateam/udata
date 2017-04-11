/**
 * Search display page JS module
 */
import FrontMixin from 'front/mixin';

import log from 'logger';
import Vue from 'vue';

// Legacy depdencies soon to be dropped
import $ from 'jquery';
import 'bootstrap';
import 'search/temporal-coverage-facet';


new Vue({
    mixins: [FrontMixin],
    ready() {
        log.debug('Search page');
        $('.advanced-search-panel .list-group-more').on('shown.bs.collapse', function() {
            $('button[data-target="#' + this.id + '"]').hide();
        });

        $('.advanced-search-panel .list-group').on('hidden.bs.collapse shown.bs.collapse', function(e) {
            // Do not flip chevrons if the "More results" link is clicked.
            if (e.target.id.endsWith('-more')) return;
            $('div[data-target="#' + this.id + '"] .chevrons').first()
                .toggleClass('fa-chevron-down fa-chevron-up');
        });
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
        }
    }
});
