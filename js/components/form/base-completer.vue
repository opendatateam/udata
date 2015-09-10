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
import BaseError from 'models/error';

import 'selectize';

class CompleterError extends BaseError {};

function lst2str(value) {
    if (Vue.util.isArray(value)) {
        return value.join(',');
    }
    return value || '';
}

function forceLst(value) {
    if (Vue.util.isArray(value)) {
        return value
    } else if (Vue.util.isString(value)) {
        return value.split(',');
    } else if (value === undefined || value === null) {
        return [];
    }
    throw new CompleterError(`Expect String or Array, not ${value}`);
}

export default {
    replace: true,
    mixins: [require('components/form/base-field').FieldComponentMixin],
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
        lst2str
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
    watch: {
        value: function(values) {
            if (this.selectize) {
                this.selectize.clear(true);
                forceLst(values).forEach((value) => {
                    this.selectize.createItem(value);
                });
            }
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
            this.selectize = undefined;
        }
    }
};
</script>
