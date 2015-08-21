<template>
<input type="text" class="form-control"
    v-attr="
        id: field && field.id || '',
        name: field && field.id || '',
        placeholder: placeholder || '',
        required: required,
        value: value | lst2str,
        readonly: readonly || false"
    />
</template>

<script>
import API from 'api';
import Vue from 'vue';
import $ from 'jquery';
import logger from 'logger';

import 'selectize';

export default {
    inherit: true,
    replace: true,
    computed: {
        selectize_options: function() {
            var opts = this.$options.selectize;

            return $.extend({},
                Vue.util.isFunction(opts) ? opts.apply(this, []) : opts,
                {
                    persist: false,
                    closeAfterSelect: true,
                    load: this.load_suggestions.bind(this),
                    onItemAdd: (value, $item) => {
                        this.$dispatch('completer:item-add', value, $item);
                        if (this.$options.selectize.onItemAdd) {
                            this.$options.selectize.onItemAdd(value, $item);
                        }
                    }
                }
            );
        }
    },
    filters: {
        lst2str: function(value) {
            if (Vue.util.isArray(value)) {
                return value.join(',');
            }
            return value || '';
        }
    },
    methods: {
        load_suggestions: function(query, callback) {
            if (!query.length) return callback();

            API[this.$options.ns][this.$options.endpoint]({
                q: query,
                size: 10
            }, (data) => {
                var content = data.obj;
                if (this.$options.dataLoaded) {
                    content = this.$options.dataLoaded(content);
                }
                callback(content);
            }, function(message) {
                log.error('Unable to fetch completion', message);
                callback();
            });
        }
    },
    ready: function() {
        if (!this.field || !this.field.readonly) {
            this.selectize = $(this.$el).selectize(this.selectize_options)[0].selectize;
        }
    },
    beforeDestroy: function() {
        if (this.selectize) {
            this.selectize.destroy();
        }
    }
};
</script>
