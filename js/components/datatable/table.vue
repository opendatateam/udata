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
            <th v-for="field in fields"
                :class="classes_for(field)"
                @click="header_click(field)"
                :width="field.width | thwidth">
                {{field.label}}
                <span class="fa fa-fw" v-if="field.sort"
                    :class="sort_classes_for(field)"></span>
            </th>
        </tr>
    </thead>
    <tbody>
        <tr v-for="item in p.data" :track-by="trackBy" is="row"
            :item="item" :fields="fields" :selected="item === selected">
        </tr>
    </tbody>
</table>
</template>

<script>
import Row from './row.vue';

export default {
    name: 'datatable',
    replace: true,
    components: {
        Row
    },
    props: {
        p: Object,
        fields: Array,
        track: {
            type: null,
            default: 'id'
        }
    },
    data: function() {
        return {
            selected: null
        };
    },
    computed: {
        remote: function() {
            return this.p && this.p.serverside;
        },
        trackBy: function() {
            return this.track || '';
        }
    },
    events: {
        'datatable:item:click': function(item) {
            this.selected = item;
            return true;
        }
    },
    methods: {
        header_click(field) {
            if (field.sort) {
                this.p.sort(this.sort_for(field));
            }
        },
        sort_for(field) {
            return this.remote ? field.sort : field.key;
        },
        classes_for(field) {
            let classes = {pointer: Boolean(field.sort)},
                align = field.align || 'left';

            classes[`text-${align}`] = true;

            return classes;
        },
        sort_classes_for(field) {
            let classes = {};

            if (this.p.sorted != this.sort_for(field)) {
                classes['fa-sort'] = true;
            } else if (!this.p.reversed) {
                classes['fa-sort-asc'] = true;
            } else if (this.p.reversed) {
                classes['fa-sort-desc'] = true;
            }

            return classes;
        }
    },
    filters: {
        thwidth(value) {
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
