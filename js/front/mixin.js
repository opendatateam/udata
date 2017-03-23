import Vue from 'vue';

/**
* Frontend views common behavior
*/
export default {
    el: 'body',
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
                el: this.$els.modal,  // This is the modal placeholder in Jinja template
                replace: false,  // Needed while all components are not migrated to replace: true behavior
                parent: this,
                propsData: data
            });
        },
    }
};
