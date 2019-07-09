<template>
<input type="text" class="form-control"
    :id="field && field.id || ''"
    :name="field && field.id || ''"
    :placeholder="placeholder || ''"
    :required="required"
    :value="value | lst2str"
    :readonly="readonly || false"
    autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
    />
</template>

<script>
import API from 'api';
import Vue from 'vue';
import $ from 'jquery';
import log from 'logger';
import CustomError from 'error';
import utils from 'utils';
import {FieldComponentMixin} from 'components/form/base-field';

import Selectize from 'selectize';

/**
 * A Selectize plugin to avoid field clearing on blur
 * Based on: https://github.com/selectize/selectize.js/issues/999#issuecomment-380382572
 */
Selectize.define('preserve-on-blur', function (options) {
    this.onBlur = ((e) => {
        var original = this.onBlur;

        return function (e) {
            // Capture the current input value
            var $input = this.$control_input;
            var inputValue = $input.val();

            // Do the default actions
            original.apply(this, [e]);

            // Set the value back                    
            this.setTextboxValue(inputValue);
        };
    })();
});


class CompleterError extends CustomError {};

function lst2str(value) {
    if (Array.isArray(value)) {
        return value.join(',');
    }
    return value || '';
}

function forceList(value) {
    if (Array.isArray(value)) {
        return value
    } else if (utils.isString(value)) {
        return value.split(',');
    } else if (value === undefined || value === null) {
        return [];
    }
    throw new CompleterError(`Expect String or Array, not ${value}`);
}

export default {
    mixins: [FieldComponentMixin],
    computed: {
        selectize_options() {
            var opts = this.$options.selectize;

            opts = $.extend({},
                utils.isFunction(opts) ? opts.apply(this, []) : opts,
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
            opts.plugins.push('preserve-on-blur');
            return opts;
        }
    },
    events: {
        'form:beforeDestroy': function() {
            this.destroy();
        }
    },
    filters: {
        lst2str
    },
    methods: {
        load_suggestions(query, callback) {
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
        },
        clear() {
            if (this.selectize) {
                this.selectize.clear(true);
                this.selectize.setTextboxValue('');
            }
        },
        destroy() {
            if (this.selectize) {
                this.selectize.destroy();
                this.selectize = undefined;
            }
        }
    },
    watch: {
        value: function(values) {
            if (this.selectize) {
                this.selectize.clear(true);
                forceList(values).forEach((value) => {
                    this.selectize.createItem(value);
                });
            }
        }
    },
    ready() {
        if (!this.field || !this.field.readonly) {
            this.selectize = $(this.$el).selectize(this.selectize_options)[0].selectize;
        }
    },
    beforeDestroy() {
        this.destroy();
    }
};
</script>

<style lang="less">
@import '~less/admin/variables';
@import '~bootstrap/less/mixins';
@import '~selectize/src/less/selectize.bootstrap3.less';

@selectize-color-item: @label-primary-bg;
@selectize-color-item-text: @label-color;
@selectize-color-item-active-text: @label-link-hover-color;
@selectize-padding-item-x: 5px;
@selectize-padding-item-y: 2px;

.selectize-control {
    .selectize-input {
        border-radius: 0;

        // Tags
        .multi& > div {
            -webkit-border-radius: 0;
               -moz-border-radius: 0;
                    border-radius: 0;
        }

        .card {
            margin: 0;
        }

        &.focus {
            border-color: #3c8dbc;
            -webkit-box-shadow: none;
                    box-shadow: none;
        }

        .form-group.has-error & {
            border-color: @red;
        }

        .form-group.has-success & {
            border-color: @green;
        }
    }

    .selectize-dropdown .selectize-option {
        padding-left: 5px;
        .logo {
            width: 25px;
            height: 25px;
            border: 1px solid @gray-lighter;
            margin-left: -5px;
            margin-right: 5px;
            img {
                width: 100%;
                max-width: 100%;
                max-height: 100%;
            }
        }

    }

    .selectize-dropdown-content > .create {
        padding: @selectize-padding-dropdown-item-y * 2 @selectize-padding-dropdown-item-x;
    }

    &.plugin-remove_button .card-input {
        position: relative;
        .card {
            margin-right: 10px;
        }

        a.remove {
            position: absolute;
            top: 0;
            right: 4px;
        }
    }

    .card-input {
        display: block;
    }

    .locked, .locked.input-active {
        cursor: not-allowed !important;
        background-color: #DCDCDC !important;
        opacity: 1;
    }

    a.remove {
        color: white;
        margin-left: 4px;

        &:hover {
            color: red;
        }
    }
}
</style>
