<style lang="less">
.date-picker {
    .dropdown-menu {
        min-width:auto;
        width:100%;
    }
}
</style>

<template>
<div class="input-group dropdown date-picker" v-class="open: picking">
    <span class="input-group-addon"><span class="fa fa-calendar"></span></span>
    <input type="text" class="form-control" v-el="input"
        v-on="focus: onFocus, blur: onBlur"
        v-attr="
            placeholder: placeholder,
            required: required,
            value: value,
            readonly: readonly || false
        "></input>
    <div class="dropdown-menu dropdown-menu-right">
        <calendar selected="{{value}}"></calendar>
    </div>
    <input type="hidden" v-el="hidden"
        v-attr="
            id: field.id,
            name: field.id,
            value: value
        "></input>
</div>
</template>

<script>
'use strict';

var DEFAULT_FORMAT = 'L',
    ISO_FORMAT = 'YYYY-MM-DD';

module.exports = {
    name: 'date-picker',
    inherit: true,
    replace: true,
    components: {
        calendar: require('components/calendar.vue')
    },
    data: function() {
        return {
            picking: false
        };
    },
    events: {
        'calendar:date:selected': function(date) {
            this.$$.input.value = date.format(this.field.format || DEFAULT_FORMAT);
            this.$$.hidden.value = date.format(ISO_FORMAT);
            this.picking = false;
        },
        'calendar:date:cleared': function() {
            this.$$.input.value = '';
            this.$$.hidden.value = '';
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
