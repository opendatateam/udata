<style lang="less">
.date-picker {
    .dropdown-menu {
        min-width:100%;
        width:auto;
    }
}
</style>

<template>
<div class="input-group dropdown date-picker" :class="{ 'open': picking }">
    <span class="input-group-addon"><span class="fa fa-calendar"></span></span>
    <input type="text" class="form-control" v-el:input
        @focus="onFocus"
        @blur="onBlur"
        :placeholder="placeholder"
        :required="required"
        :value="value|dateFormatted"
        :readonly="readonly"></input>
    <div class="dropdown-menu dropdown-menu-right">
        <calendar selected="{{value}}"></calendar>
    </div>
    <input type="hidden" v-el:hidden
        :id="field.id"
        :name="serializable ? field.id : ''"
        :value="value"></input>
</div>
</template>

<script>
import moment from 'moment';

const DEFAULT_FORMAT = 'L';
const ISO_FORMAT = 'YYYY-MM-DDTHH:mm:ss';

export default {
    name: 'date-picker',
    replace: true,
    mixins: [require('components/form/base-field').FieldComponentMixin],
    props: ['serializable'],
    components: {
        calendar: require('components/calendar.vue')
    },
    data: function() {
        return {
            picking: false,
            serializable: true
        };
    },
    filters: {
        dateFormatted: function(value) {
            // Will default to current day if value is null or empty.
            return value
                   ? moment(value).format(this.field.format || DEFAULT_FORMAT)
                   : '';
        }
    },
    events: {
        'calendar:date:selected': function(date) {
            this.$els.input.value = date.format(this.field.format || DEFAULT_FORMAT);
            this.$els.hidden.value = date.format(ISO_FORMAT);
            this.picking = false;
        },
        'calendar:date:cleared': function() {
            this.$els.input.value = '';
            this.$els.hidden.value = '';
            this.picking = false;
        }
    },
    methods: {
        onFocus: function() {
            this.picking = true;
        },
        onBlur: function(e) {
            if (e.targetVM !== this) {
                this.picking = false;
            }
        }
    }
};
</script>
