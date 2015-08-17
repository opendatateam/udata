<style lang="less">
.datatable-widget {
    td.avatar-cell {
        padding: 3px;
    }

    th {
        white-space: nowrap;
    }

    td.ellipsis {
        white-space: nowrap;
        overflow: hidden;
        text-overflow:ellipsis;
        max-width: 0;
    }

    header.datatable-header > header{
        width: 100%;
        padding: 10px;
    }
}
</style>

<template>
<box title="{{ title }}" icon="{{ icon }}"
    boxclass="datatable-widget {{tint ? 'box-' + tint : 'box-solid'}} {{boxclass}}"
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
                    v-model="search_query" debounce="500" v-on="keyup:search | key enter">
                <div class="input-group-btn">
                    <button class="btn btn-sm btn-flat" v-on="click: search">
                        <i class="fa fa-search"></i>
                    </button>
                </div>
            </div>
        </div>
    </aside>
    <header class="datatable-header">
        <content select="header"></content>
    </header>
    <table class="table table-hover" v-if="has_data">
        <thead>
            <tr>
                <th class="text-{{field.align || 'left'}}"
                    v-class="pointer: sort"
                    v-repeat="field in fields"
                    v-on="click: header_click(field)"
                    v-attr="width: field.width | thwidth">
                    {{field.label}}
                    <span class="fa fa-fw" v-if="field.sort" v-class="
                        fa-sort: p.sorted != sort_for(field),
                        fa-sort-asc: p.sorted == sort_for(field) && !p.reversed,
                        fa-sort-desc: p.sorted == sort_for(field) && p.reversed
                    "></span>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr class="pointer"
                v-repeat="item in p.data"
                v-class="active: selected == item"
                v-on="click: item_click(item)">
                <td v-repeat="field in fields" track-by="key"
                    v-class="
                        text-center: field.align === 'center',
                        text-left: field.align === 'left',
                        text-right: field.align === 'right',
                        ellipsis: field.ellipsis
                    ">
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
import Vue from 'vue';
import $ from 'jquery';
import placeholders from 'helpers/placeholders';

const VISIBILITIES = {
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

const CellWidget = {
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
                    if (!result || !result.hasOwnProperty(key)) {
                        result = null;
                        break;
                    }
                    result = result[key];
                }
            }

            return result || this.$options.default;
        }
    }
};

export default {
    name: 'datatable-widget',
    components: {
        'box': require('components/containers/box.vue'),
        'pagination-widget': require('components/pagination.vue'),
        'text': {
            mixins: [CellWidget],
            template: '{{value}}'
        },
        'date': {
            mixins: [CellWidget],
            template: [
                '<time datetime="{{value | dt YYYY-MM-DD }}" v-if="value">',
                '{{value | dt L }}',
                '</time>',
                '<span v-if="!value">-</span>'
            ].join('')
        },
        'datetime': {
            mixins: [CellWidget],
            template: [
                '<time datetime="{{value}}" v-if="value">',
                '{{value | dt L LT }}',
                '</time>',
                '<span v-if="!value">-</span>'
            ].join('')
        },
        'timeago': {
            mixins: [CellWidget],
            template: [
                '<time datetime="{{value}}" class="timeago" v-if="value">',
                '{{value | timeago }}',
                '</time>',
                '<span v-if="!value">-</span>'
            ].join('')
        },
        'since': {
            mixins: [CellWidget],
            template: '<time datetime="{{value}}">{{value | since }}</time>'
        },
        'label': {
            mixins: [CellWidget],
            template: '<span class="label label-{{color}}">{{label}}</span>',
            computed: {
                color: function() {
                    return this.field.label_type(this.value);
                },
                label: function() {
                    return this.field.hasOwnProperty('label_func')
                        ? this.field.label_func(this.value)
                        : this.value;
                }
            }
        },
        'avatar': {
            mixins: [CellWidget],
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
        },
        'metric': {
            mixins: [CellWidget],
            default: 0,
            template: [
                '<span class="badge" v-class="bg-green: value > 0, bg-red: value == 0">',
                '{{value}}',
                '</span>'
            ].join(''),
        },
        'visibility': {
            mixins: [CellWidget],
            template: '<span class="label label-{{type}}">{{text}}</span>',
            computed: {
                type: function() {
                    if (!this.item) return;
                    if (this.item.deleted) {
                        return VISIBILITIES.deleted.type;
                    } else if (this.item.private) {
                        return VISIBILITIES.private.type;
                    } else {
                        return VISIBILITIES.public.type;
                    }
                },
                text: function() {
                    if (!this.item) return;
                    if (this.item.deleted) {
                        return VISIBILITIES.deleted.label;
                    } else if (this.item.private) {
                        return VISIBILITIES.private.label;
                    } else {
                        return VISIBILITIES.public.label;
                    }
                }
            }
        },
        'playpause': {
            mixins: [CellWidget],
            default: false,
            template: `<i class="fa fa-fw fa-{{value ? 'play' : 'stop'}} text-{{value ? 'green' : 'red'}}"></i>`,
        }
    },
    data: function() {
        return {
            search_query: null,
            downloads: [],
            p: {},
            track: 'id',
            selected: null,
            fields: []
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
        },
        trackBy: function() {
            return this.track || '';
        }
    },
    props: ['p', 'title', 'icon', 'fields', 'boxclass', 'tint', 'downloads', 'empty', 'track'],
    methods: {
        search: function() {
            this.p.search(this.search_query);
        },
        item_click: function(item) {
            this.selected = item;
            this.$dispatch('datatable:item:click', item);
        },
        header_click: function(field) {
            if (field.sort) {
                this.p.sort(this.remote ? field.sort : field.key);
            }
        },
        sort_for: function(field) {
            return this.remote ? field.sort : field.key;
        }
    },
    filters: {
        thwidth: function(value) {
            switch(value) {
                case undefined:
                    return '';
                case 0:
                    return 0;
                default:
                    return value + 5;
            }
        }
    },
    watch: {
        search_query: function(query) {
            this.p.search(query);
        }
    }
};
</script>
