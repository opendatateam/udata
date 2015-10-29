<style lang="less">
.datatable-widget {
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
    loading="{{ loading === undefined ? p.loading : loading }}">
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
                    v-model="search_query" debounce="500" @keyup="search | key enter">
                <div class="input-group-btn">
                    <button class="btn btn-sm btn-flat" @click="search">
                        <i class="fa fa-search"></i>
                    </button>
                </div>
            </div>
        </div>
    </aside>
    <header class="datatable-header">
        <content select="header"></content>
    </header>
    <datatable v-if="has_data" p="{{p}}" fields="{{fields}}" track="{{track}}">
    </datatable>
    <div class="text-center lead" v-if="!has_data">
    {{ empty || _('No data')}}
    </div>
    <footer>
        <div :class="{ 'pull-right': p.pages > 1 }" v-el="footer_container">
            <content select="footer"></content>
        </div>
        <pagination-widget p="{{p}}"></pagination-widget>
    </footer>
</box>
</template>

<script>
export default {
    name: 'datatable-widget',
    components: {
        'box': require('components/containers/box.vue'),
        'datatable': require('components/datatable/table.vue'),
        'pagination-widget': require('components/pagination.vue'),
    },
    data: function() {
        return {
            search_query: null,
            downloads: [],
            p: {},
            track: 'id',
            selected: null,
            fields: [],
            loading: undefined
        };
    },
    computed: {
        show_footer: function() {
            return (this.p && this.p.pages > 1)
                || $(this.$$.footer_container).find('footer > *').length;
        },
        has_data: function() {
            return this.p.data && this.p.data.length;
        }
    },
    props: [
        'p',
        'title',
        'icon',
        'fields',
        'boxclass',
        'tint',
        'downloads',
        'empty',
        'track',
        'loading'
    ],
    methods: {
        search: function() {
            this.p.search(this.search_query);
        }
    },
    watch: {
        search_query: function(query) {
            this.p.search(query);
        }
    }
};
</script>
