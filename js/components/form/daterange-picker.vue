<style lang="less">
.daterange-picker {
    .dropdown-menu {
        min-width: auto;
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
        :value="startValue|dt dateFormat ''"
        :readonly="readonly">
    <span class="input-group-addon">{{ _('to') }}</span>
    <input type="text" class="input-sm form-control"
        v-el:end-input :placeholder="_('End')"
        @focus="onFocus"
        :required="required"
        :value="endValue|dt dateFormat ''"
        :readonly="readonly">
    <div class="dropdown-menu" :style="dropdownStyle">
        <calendar :selected="currentValue" :min="dateMin" :max="dateMax"></calendar>
    </div>
    <input type="hidden" v-el:start-hidden
        :id="startId" :name="startId"
        :value="startValue|dt ISO_FORMAT ''"></input>
    <input type="hidden" v-el:end-hidden
        :id="endId" :name="endId"
        :value="endValue|dt ISO_FORMAT ''"></input>
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
            startValue: this.value && this.value.hasOwnProperty('start') ? this.value.start : '',
            endValue: this.value && this.value.hasOwnProperty('end') ? this.value.end : '',
            ISO_FORMAT
        };
    },
    computed: {
        currentValue: {
            get() {
                return this.pickedField === this.$els.startInput ? this.startValue : this.endValue;
            },
            set(value) {
                if (this.pickedField === this.$els.startInput) {
                    this.startValue = value;
                } else {
                    this.endValue = value;
                }
            }
        },
        startId() {
            return `${this.field.id}.start`;
        },
        endId() {
            return `${this.field.id}.end`;
        },
        dateMin() {
            if (this.pickedField === this.$els.endInput) {
                return this.startValue || undefined;
            }
        },
        dateMax() {
            if (this.pickedField === this.$els.startInput) {
                return this.endValue || undefined;
            }
        },
        dateFormat() {
            return this.field.format || DEFAULT_FORMAT;
        },
        dropdownStyle() {
            if (!this.pickedField) return {};
            const outerBox = this.$el.getBoundingClientRect();
            const box = this.pickedField.getBoundingClientRect();
            return {
                width: `${box.width}px`,
                left: `${box.left - outerBox.left}px`,
                top: `${box.height}px`,
            };
        }
    },
    events: {
        'calendar:date:selected': function(date) {
            this.currentValue = date;
            this.picking = false;
            return true;
        },
        'calendar:date:cleared': function() {
            this.currentValue = null;
            this.picking = false;
            return true;
        }
    },
    ready() {
        // Perform all validations on end field because performing on start field unhighlight.
        $(this.$els.endHidden).rules('add', {
            dateGreaterThan: this.$els.startHidden.id,
            required: (el) => {
                return (this.startValue && !this.endValue) || (this.endValue && !this.startValue);
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
        },
        onOutside() {
            this.picking = false;
        }
    },
    watch: {
        value(value) {
            this.startValue = this.value && this.value.hasOwnProperty('start') ? this.value.start : '';
            this.endValue = this.value && this.value.hasOwnProperty('end') ? this.value.end : '';
        }
    }
};
</script>
