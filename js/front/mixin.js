import Vue from 'vue';
import NotificationZone from 'components/notification-zone.vue';

/**
* Frontend views common behavior
*/
export default {
    el: 'body',
    components: {NotificationZone},
    data() {
        return {
            notifications: [],
        };
    },
    events: {
        'notify:success': function(title, details) {
            this.notifications.push({type: 'success', icon: 'check', title, details});
        },
        'notify:error': function(title, details) {
            this.notifications.push({type: 'danger', icon: 'exclamation-triangle', title, details});
        },
        'notify:close': function(notification) {
            const index = this.notifications.indexOf(notification);
            this.notifications.splice(index, 1);
        }
    },
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
