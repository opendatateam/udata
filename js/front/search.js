/**
 * Search display page JS module
 */
import FrontMixin from 'front/mixin';

import log from 'logger';
import Vue from 'vue';
import velocity from 'velocity-animate';

// Legacy depdencies soon to be dropped
import 'search/temporal-coverage-facet';


new Vue({
    mixins: [FrontMixin],
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
        /**
         * Collapse or open a facet panel
         * @param  {String} id The panel identifier to toggle
         */
        togglePanel(id) {
            const panel = document.getElementById(`facet-${id}`);
            const chevrons = document.getElementById(`chevrons-${id}`);
            if (panel.classList.contains('in')) {
                velocity(panel, 'slideUp', {duration: 500}).then(() => {
                    panel.classList.remove('in');
                });
            } else {
                velocity(panel, 'slideDown', {duration: 500}).then(() => {
                    panel.classList.add('in');
                });
            }
            chevrons.classList.toggle('fa-chevron-up');
            chevrons.classList.toggle('fa-chevron-down');
        },
        /**
         * Expand a panel (diplay more details)
         * @param  {String} id The panel identifier to expand
         */
        expandPanel(id, evt) {
            evt.target.remove();
            const panel = document.getElementById(`facet-${id}-more`);
            velocity(panel, 'slideDown', {duration: 500}).then(() => {
                panel.classList.add('in');
            });
        }
    }
});
