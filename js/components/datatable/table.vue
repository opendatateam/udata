<style lang="less">
.datatable {
    th {
        white-space: nowrap;
    }
}
</style>

<template>
<table class="table table-hover datatable">
    <thead>
        <tr>
            <th class="text-{{field.align || 'left'}}"
                :class="{ 'pointer': field.sort }"
                v-repeat="field in fields"
                @click="header_click(field)"
                v-attr="width: field.width | thwidth">
                {{field.label}}
                <span class="fa fa-fw" v-if="field.sort" :class="{
                    'fa-sort': p.sorted != sort_for(field),
                    'fa-sort-asc': p.sorted == sort_for(field) && !p.reversed,
                    'fa-sort-desc': p.sorted == sort_for(field) && p.reversed
                }"></span>
            </th>
        </tr>
    </thead>
    <tbody>
        <tr v-repeat="item in p.data" track-by="{{trackBy}}"
            v-component="row"
            fields="{{fields}}"
            selected="{{item === selected}}">
        </tr>
    </tbody>
</table>
</template>

<script>
export default {
    name: 'datatable',
    replace: true,
    components: {
        'row': require('./row.vue'),
    },
    props: ['p', 'fields', 'track'],
    data: function() {
        return {
            p: {},
            track: 'id',
            selected: null,
            fields: []
        };
    },
    computed: {
        remote: function() {
            return this.p && this.p.serverside;
        },
        show_footer: function() {
            return (this.p && this.p.pages > 1)
                || $(this.$els.footer_container).find('footer > *').length;
        },
        has_data: function() {
            return this.p.data && this.p.data.length;
        },
        trackBy: function() {
            return this.track || '';
        }
    },
    events: {
        'datatable:item:click': function(item) {
            this.selected = item;
        }
    },
    methods: {
        header_click: function(field) {
            if (field.sort) {
                this.p.sort(this.sort_for(field));
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
    }
};
</script>
