<style lang="less">
.datatable-widget {
    td.avatar-cell {
        padding: 3px;
    }
}
</style>

<template>
<box title="{{ title }}" icon="{{ icon }}"
    boxclass="box-solid datatable-widget {{boxclass}}"
    bodyclass="table-responsive no-padding"
    footerclass="text-center clearfix"
    footer="{{ show_footer }}"
    loading="{{ p.loading }}">
    <aside>
        <div class="btn-group" v-show="downloads && downloads.length">
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
    </aside>
    <table class="table table-hover" v-if="has_data">
        <thead>
            <tr>
                <th class="text-{{align || 'left'}}"
                    v-class="pointer: sort"
                    v-repeat="fields" v-on="click: sort ? p.sort(remote ? sort : key) : null"
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
    <div class="text-center lead" v-if="!has_data">
    {{ empty || _('No data')}}
    </div>
    <footer>
        <div v-class="pull-right: p.pages > 1" v-el="footer_container">
            <content select="footer"></content>
        </div>
        <pagination-widget p="{{p}}"></pagination-widget>
    </footer>
</box>
</template>

<script>
'use strict';

var Vue = require('vue'),
    $ = require('jquery'),
    placeholders = require('helpers/placeholders'),
    VISIBILITIES = {
        deleted: {
            label: Vue._('Deleted'),
            type: 'error'
        },
        private: {
            label: Vue._('Private'),
            type: 'warning'
        },
        public: {
            label: Vue._('Public'),
            type: 'info'
        }
    };

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

            if (Vue.util.isFunction(this.field.key)) {
                result = this.field.key(this.item);
            } else {
                var parts = this.field.key.split('.'),
                    result = this.item;

                for (var i=0; i < parts.length; i++) {
                    var key = parts[i];
                    result = result[key];
                }
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
    components: {
        'box': require('components/containers/box.vue'),
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
        }),
        'visibility': CellWidget.extend({
            template: '<span class="label label-{{type}}">{{text}}</span>',
            computed: {
                type: function() {
                    if (this.item.deleted) {
                        return VISIBILITIES.deleted.type;
                    } else if (this.item.private) {
                        return VISIBILITIES.private.type;
                    } else {
                        return VISIBILITIES.public.type;
                    }
                },
                text: function() {
                    if (this.item.deleted) {
                        return VISIBILITIES.deleted.label;
                    } else if (this.item.private) {
                        return VISIBILITIES.private.label;
                    } else {
                        return VISIBILITIES.public.label;
                    }
                }
            }
        })
    },
    data: function() {
        return {
            search_query: null,
            downloads: [],
            p: {}
        };
    },
    computed: {
        remote: function() {
            return this.p && (this.p.serverside == true);
        },
        show_footer: function() {
            return (this.p && this.p.pages > 1)
                || $(this.$$.footer_container).find('footer > *').length;
        },
        has_data: function() {
            return this.p.data && this.p.data.length;
        }
    },
    props: ['p', 'title', 'icon', 'fields', 'boxclass', 'downloads', 'empty'],
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
