<style lang="less">
.time-picker {
    .dropdown-menu {
        min-width:100%;
        width:auto;
        margin: 0;
    }
}
</style>

<template>
<div class="input-group dropdown time-picker" :class="{ 'open': picking }">
    <span class="input-group-addon"><span class="fa fa-clock-o"></span></span>
    <input type="text" class="form-control" v-el:input
        @focus="onFocus"
        @blur="onBlur"
        :placeholder="placeholder"
        :required="required"
        :value="value|timeFormatted"
        :readonly="readonly || false"></input>
    <div class="dropdown-menu dropdown-menu-right">
        <time-widget :selected="value"></time-widget>
    </div>
    <input type="hidden" v-el:hidden
        :id="field.id"
        :name="serializable ? field.id : ''"
        :value="value"></input>
</div>
</template>

<script>
import moment from 'moment';
import {FieldComponentMixin} from 'components/form/base-field';

const DEFAULT_FORMAT = 'HH:mm';
const ISO_FORMAT = 'YYYY-MM-DDTHH:mm:ss';

export default {
    name: 'time-picker',
    replace: true,
    props: ['serializable'],
    mixins: [FieldComponentMixin],
    components: {
        'time-widget': require('components/time-widget.vue')
    },
    data: function() {
        return {
            picking: false
        };
    },
    filters: {
        timeFormatted: function(value) {
            return value ? moment(value).format(this.field.format || DEFAULT_FORMAT) : '';
        }
    },
    events: {
        'calendar:time:selected': function(date) {
            this.$els.input.value = date.format(this.field.format || DEFAULT_FORMAT);
            this.$els.hidden.value = date.format(ISO_FORMAT);
            this.picking = true;
        },

        'calendar:time:close': function() {
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
