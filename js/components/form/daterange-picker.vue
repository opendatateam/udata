<style lang="less">
.daterange-picker {
    .dropdown-menu {
        min-width:auto;
        width:100%;
    }
}
</style>

<template>
<div class="input-group dropdown daterange-picker" :class="{ 'open': picking }"
    v-outside="onOutside">
    <span class="input-group-addon"><span class="fa fa-calendar"></span></span>
    <input type="text" class="input-sm form-control"
        v-el:start-input :placeholder="_('Start')"
        @focus="onFocus"
        :required="required"
        :value="start_value|dt date_format ''"
        :readonly="readonly">
    <span class="input-group-addon">{{ _('to') }}</span>
    <input type="text" class="input-sm form-control"
        v-el:end-input :placeholder="_('End')"
        @focus="onFocus"
        :required="required"
        :value="end_value|dt date_format ''"
        :readonly="readonly">
    <div class="dropdown-menu dropdown-menu-right">
        <calendar :selected="current_value"></calendar>
    </div>
    <input type="hidden" v-el:start-hidden
        :id="field.id + '.start'"
        :name="field.id + '.start'"
        :value="start_value"></input>
    <input type="hidden" v-el:end-hidden
        :id="field.id + '.end'"
        :name="field.id + '.end'"
        :value="end_value"></input>
</div>
</template>

<script>
import Calendar from 'components/calendar.vue';
import {FieldComponentMixin} from 'components/form/base-field';
import $ from 'jquery';

const DEFAULT_FORMAT = 'L';
const ISO_FORMAT = 'YYYY-MM-DD';


export default {
    name: 'daterange-picker',
    replace: true,
    mixins: [FieldComponentMixin],
    components: {Calendar},
    data() {
        return {
            picking: false,
            pickedField: null,
            hiddenField: null
        };
    },
    computed: {
        start_value() {
            return this.value && this.value.hasOwnProperty('start')
                ? this.value.start
                : '';
        },
        end_value() {
            return this.value && this.value.hasOwnProperty('end')
                ? this.value.end
                : '';
        },
        current_value() {
            if (this.hiddenField) {
                return this.hiddenField.value;
            }
        },
        date_format() {
            return this.field.format || DEFAULT_FORMAT;
        }
    },
    events: {
        'calendar:date:selected': function(date) {
            this.pickedField.value = date.format(this.date_format);
            this.hiddenField.value = date.format(ISO_FORMAT);
            this.picking = false;
            return true;
        },
        'calendar:date:cleared': function() {
            this.pickedField.value = '';
            this.hiddenField.value = '';
            this.picking = false;
            return true;
        }
    },
    ready() {
        // Perform all validations on end field because performing on start field unhighlight.
        $(this.$els.endHidden).rules('add', {
            dateGreaterThan: '#' + this.$els.startHidden.id,
            required: (el) => {
                return (this.$els.startHidden.value && !this.$els.endHidden.value) || (this.$els.endHidden.value && !this.$els.startHidden.value);
            },
            messages: {
                dateGreaterThan: this._('End date should be after start date'),
                required: this._('Both dates are required')
            }
        });
    },
    methods: {
        onFocus(e) {
            this.picking = true;
            this.pickedField = e.target;
            this.hiddenField = e.target == this.$els.startInput
                ? this.$els.startHidden
                : this.$els.endHidden;
        },
        onOutside() {
            this.picking = false;
        }
    }
};
</script>
