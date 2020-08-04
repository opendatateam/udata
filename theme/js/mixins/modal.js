import Vue from 'vue';

/**
 * A mixin holding the modal container Behavior.
 * @type {Object}
 */
export default {
    methods: {
        /**
         * Insert a modal Vue in the application.
         * @param  {Object} options     The modal component definition (options passed to Vue.extend())
         * @param  {Object} propsData   Data to assign to modal properties
         * @return {Vue}                The child instanciated vm
         */
        $modal(options, propsData) {
            const constructor = Vue.extend(options);
            const el = document.createElement('div');
            this.$els.modal.appendChild(el);
            const modal = new constructor({el, parent: this, propsData});
            modal.$on('modal:closed', modal.$destroy);
            return modal;
        }
    }
};
