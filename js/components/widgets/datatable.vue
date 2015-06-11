<style lang="less">
.datatable-widget {
    td.avatar-cell {
        padding: 3px;
    }

    .btn-box-tool {
        font-size: 14px;
        padding: 6px 8px;
    }
}
</style>

<template>
    <div class="box box-solid datatable-widget {{boxclass}}">
        <header class="box-header" v-show="title || icon">
            <i v-show="icon" class="fa fa-{{icon}}"></i>
            <h3 class="box-title">{{title}}</h3>
            <div class="box-tools">
                <div class="box-search" v-if="p.has_search">
                    <div class="input-group">
                        <input type="text" class="form-control input-sm pull-right"
                            style="width: 150px;" placeholder="{{'Search'|i18n}}"
                            v-model="search_query" v-on="keyup:search | key enter">
                        <div class="input-group-btn">
                            <button class="btn btn-sm btn-flat">
                                <i class="fa fa-search"></i>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="btn-group pull-right" v-if="downloads.length">
                    <button type="button" class="btn btn-box-tool dropdown-toggle"
                        data-toggle="dropdown" aria-expanded="false">
                        <span class="fa fa-download"></span>
                    </button>
                    <ul class="dropdown-menu" role="menu">
                        <li v-repeat="downloads">
                            <a href="{{url}}">{{label}}</a>
                        </li>
                    </ul>
                </div>
            </div>
        </header>
        <div class="box-body table-responsive no-padding">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th class="pointer text-{{align || 'left'}}"
                            v-repeat="fields" v-on="click: p.sort(remote ? sort : key)"
                            v-attr="width: width + 5">
                            {{label}}
                            <span class="fa fa-fw" v-if="sort" v-class="
                                fa-sort: p.sorted != (remote ? sort : key),
                                fa-sort-asc: p.sorted == (remote ? sort : key) && !p.reversed,
                                fa-sort-desc: p.sorted == (remote ? sort : key) && p.reversed
                            "></span>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="pointer"
                        v-repeat="item:p.data" track-by="id"
                        v-on="click: item_click(item)">
                        <td v-repeat="field: fields" track-by="key">
                            <component is="{{field.type || 'text'}}"
                                item="{{item}}" field="{{field}}">
                            </component>

                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="overlay" v-show="!p || p.loading">
            <span class="fa fa-refresh fa-spin"></span>
        </div>
        <div class="box-footer text-center clearfix">
            <content select="footer > *"></content>
            <pagination-widget p="{{p}}"></pagination-widget>
        </div>
    </div>
</template>

<script>
'use strict';

var Vue = require('vue'),
    $ = require('jquery'),
    placeholders = require('helpers/placeholders');

var CellWidget = Vue.extend({
    default: '',
    props: ['field', 'item'],
    data: function() {
        return {
            item: {},
            field: {}
        };
    },
    computed: {
        value: function() {
            if (!this.field || !this.item) {
                return this.$options.default;
            }
            var parts = this.field.key.split('.'),
                result = this.item;

            for (var i=0; i < parts.length; i++) {
                var key = parts[i];
                result = result[key];
            }

            return result || this.$options.default;
        }
    },
    attached: function() {
        // Dirty hack to fix class on field/td iteration
        if (this.field.align) {
            $(this.$el).closest('td').addClass('text-'+this.field.align);
        }
    }
})

module.exports = {
    name: 'datatable-widget',
    replace: true,
    components: {
        'pagination-widget': require('components/pagination.vue'),
        'text': CellWidget.extend({
                default: '',
                template: '{{value | truncate 100}}'
            }),
        'date': CellWidget.extend({
                template: [
                    '<time datetime="{{value | dt YYYY-MM-DD }}" v-if="value">',
                    '{{value | dt L }}',
                    '</time>',
                    '<span v-if="!value">-</span>'
                ].join('')
            }),
        'datetime': CellWidget.extend({
                template: [
                    '<time datetime="{{value}}" v-if="value">',
                    '{{value | dt L LT }}',
                    '</time>',
                    '<span v-if="!value">-</span>'
                ].join('')
            }),
        'timeago': CellWidget.extend({
                template: [
                    '<time datetime="{{value}}" class="timeago" v-if="value">',
                    '{{value | timeago }}',
                    '</time>',
                    '<span v-if="!value">-</span>'
                ].join('')
            }),
        'since': CellWidget.extend({
                template: '<time datetime="{{value}}">{{value | since }}</time>'
            }),
        'label': CellWidget.extend({
            template: '<span class="label label-{{color}}">{{value}}</span>',
            computed: {
                color: function() {
                    return this.field.label_type(this.value)
                }
            }
        }),
        'avatar': CellWidget.extend({
            template: '<img v-attr="src:src, width:field.width, height:field.width" />',
            attached: function() {
                // Dirty hack to fix class on field/td iteration
                $(this.$el).closest('td').addClass('avatar-cell');
            },
            computed: {
                src: function() {
                    if (this.value) {
                        return this.value;
                    } else if (this.field.placeholder) {
                        return placeholders[this.field.placeholder];
                    } else {
                        return placeholders.default;
                    }
                }
            }
        }),
        'metric': CellWidget.extend({
                default: 0,
                template: [
                    '<span class="badge" v-class="bg-green: value > 0, bg-red: value == 0">',
                    '{{value}}',
                    '</span>'
                ].join(''),
            })
    },
    data: function() {
        return {
            search_query: null,
            downloads: []
        };
    },
    computed: {
        remote: function() {
            return this.p && (this.p.serverside == true);
        }
    },
    props: ['p', 'title', 'icon', 'fields', 'boxclass', 'downloads'],
    methods: {
        search: function() {
            this.p.search(this.search_query);
        },
        item_click: function(item) {
            this.$dispatch('datatable:item:click', item);
        }
    }
};
</script>
