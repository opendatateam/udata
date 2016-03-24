<style lang="less">
.datatable-widget {
    header.datatable-header > header{
        width: 100%;
        padding: 10px;
    }
}
</style>

<template>
<box :title="title" :icon="icon"
    :boxclass="boxclasses"
    bodyclass="table-responsive no-padding"
    footerclass="text-center clearfix"
    :loading="loading !== undefined ? loading : p.loading"
    :footer="show_footer">
    <aside slot="tools">
        <div class="btn-group" v-show="downloads.length">
            <button type="button" class="btn btn-box-tool dropdown-toggle"
                data-toggle="dropdown" aria-expanded="false">
                <span class="fa fa-download"></span>
            </button>
            <ul class="dropdown-menu" role="menu">
                <li v-for="download in downloads">
                    <a :href="download.url">{{download.label}}</a>
                </li>
            </ul>
        </div>
        <div class="box-search" v-if="p.has_search">
            <div class="input-group">
                <input type="text" class="form-control input-sm pull-right"
                    style="width: 150px;" :placeholder="_('Search')"
                    v-model="search_query" debounce="500" @keyup.enter="search">
                <div class="input-group-btn">
                    <button class="btn btn-sm btn-flat" @click="search">
                        <i class="fa fa-search"></i>
                    </button>
                </div>
            </div>
        </div>
    </aside>
    <header class="datatable-header">
        <slot name="header"></slot>
    </header>
    <datatable v-if="p.has_data" :p="p" :fields="fields" :track="track">
    </datatable>
    <div class="text-center lead" v-if="!p.has_data">
    {{ empty || _('No data')}}
    </div>
    <footer slot="footer">
        <div :class="{ 'pull-right': p.pages > 1 }" v-el:footer_container>
            <slot name="footer"></slot>
        </div>
        <pagination-widget :p="p"></pagination-widget>
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
            selected: null,
        };
    },
    computed: {
        has_footer_children() {
            return this.$els.footer_container
                && this.$els.footer_container.children.length;
        },
        show_footer() {
            return (this.p && this.p.pages > 1) || this.has_footer_children;
        },
        boxclasses() {
            return [
                'datatable-widget',
                this.tint ? 'box-' + this.tint : 'box-solid',
                this.boxclass
            ].join(' ');
        }
    },
    props: {
        p: Object,
        title: String,
        icon: String,
        fields: Array,
        boxclass: String,
        tint: String,
        empty: String,
        loading: Boolean,
        track: {
            type: null,
            default: 'id'
        },
        downloads: {
            type: Array,
            default: function() {return [];}
        }
    },
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
