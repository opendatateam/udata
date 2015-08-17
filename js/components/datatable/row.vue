<template>
<tr class="pointer"
    v-class="active: selected"
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
</template>

<script>
export default {
    name: 'datatable-row',
    components: {
    },
    data: function() {
        return {
            track: 'id',
            selected: false,
            fields: []
        };
    },
    computed: {
        remote: function() {
            return this.p && (this.p.serverside == true);
        },
        trackBy: function() {
            return this.track || '';
        }
    },
    props: ['item', 'fields', 'selected', 'track'],
    methods: {
        item_click: function(item) {
            this.$dispatch('datatable:item:click', item);
        }
    }
};
</script>
