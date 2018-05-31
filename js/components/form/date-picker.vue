<style lang="less">
.date-picker {
    .dropdown-menu {
        min-width: 100%;
        width: auto;
    }
}
</style>

<template>
<div class="input-group dropdown date-picker" :class="{ 'open': picking }"
    v-outside="onOutside">
    <span class="input-group-addon"><span class="fa fa-calendar"></span></span>
    <input type="text" class="form-control" v-el:input
        @focus="onFocus" @input="onChange | debounce 500"
        :placeholder="placeholder"
        :required="required"
        :value="value|dt dateFormat ''"
        :readonly="readonly"></input>
    <div class="dropdown-menu dropdown-menu-right">
        <calendar v-ref:calendar :selected="value"></calendar>
    </div>
    <input v-if="serializable" v-el:hidden type="hidden"
        :name="field.id"
        :value="value|dt ISO_FORMAT ''">
    </input>
</div>
</template>

<script>
import moment from 'moment';
import Calendar from 'components/calendar.vue';
import {FieldComponentMixin} from 'components/form/base-field';

const DEFAULT_FORMAT = 'L';
const ISO_FORMAT = 'YYYY-MM-DDTHH:mm:ss';

export default {
    name: 'date-picker',
    mixins: [FieldComponentMixin],
    props: {
        serializable: {
            type: Boolean,
            default: true
        }
    },
    components: {Calendar},
    data() {
        return {
            picking: false,
            ISO_FORMAT,
        };
    },
    computed: {
        dateFormat() {
            return this.field.format || DEFAULT_FORMAT;
        }
    },
    events: {
        'calendar:date:selected': function(date) {
            this.value = date
            this.picking = false;
            return true;
        },
        'calendar:date:cleared': function() {
            this.value = null;
            this.picking = false;
            return true;
        }
    },
    methods: {
        onFocus() {
            if (!this.picking) this.$nextTick(this.$refs.calendar.focus);
            this.picking = true;
        },
        onChange(e) {
            try {
                this.value = moment(e.target.value, this.dateFormat);
            } catch(e) {
                // Don't do anything while typing (ie. incomplete date is unparseable)
            }
        },
        onOutside() {
            this.picking = false;
        }
    }
};
</script>
