<template>
    <dashboard-row v-for="row in layout"></dashboard-row>
</template>

<script>
'use strict';

module.exports = {
    name: 'DashboardView',
    props: ['layout', 'editable', 'widgets'],
    data: function() {
        return {
            layout: []
        };
    },
    components: {
        'dashboard-row': require('components/dashboard/row.vue')
    },
    methods: {
        /**
         * Asynchronously load widget (Webpack Lazy loading compatible)
         * @param  {string}   name     the filename (basename) of the view to load.
         * @param  {Function} callback An optionnal callback executed
         *                             in the application scope when
         *                             the view is loaded
         */
        loadWidget: function(name, callback) {

            var self = this,
                cb = function() {
                    callback.apply(this, [self.$.content]);
                }.bind(this);

            if (this.$options.components.hasOwnProperty(name)) {
                this.view = name;
                if (callback) {
                    Vue.nextTick(cb);
                }
            } else {
                require(['./widgets/' + name + '.vue'], function(options) {
                    self.$options.components[name] = Vue.extend(options);
                    self.view = name;
                    if (callback) {
                        Vue.nextTick(cb);
                    }
                });
            }
        }
    },
    directive
};
</script>
