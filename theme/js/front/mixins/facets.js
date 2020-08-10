/**
 * Facets handling mixin
 */
import velocity from 'velocity-animate';

import TemporalCoverageFacet from 'components/facets/temporal-coverage.vue';


export default {
    components: {TemporalCoverageFacet},
    methods: {
        /**
         * Collapse or open a facet panel
         * @param  {String} id The panel identifier to toggle
         */
        togglePanel(id, evt) {
            const panel = document.getElementById(`facet-${id}`);
            const removeBtn = document.getElementById(`facet-${id}-remove`);
            if (removeBtn && removeBtn.contains(evt.target)) return;  // Do not react on remove button click
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
};
