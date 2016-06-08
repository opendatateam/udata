<style lang="less">
.datetime-picker {
    .date-picker, .time-picker {
        width: 48%;
        float: left;
        margin: 0 1%;
    }
}
</style>

<template>
<div class="datetime-picker">
    <date-picker v-ref:date :serializable="false"></date-picker>
    <time-picker v-ref:time :serializable="false"></time-picker>
    <input type="hidden" v-el:hidden
        :id="field.id"
        :name="field.id"
        :value="value"></input>
</div>
</template>

<script>
import moment from 'moment';
import {FieldComponentMixin} from 'components/form/base-field';

export default {
    name: 'datetime-picker',
    replace: true,
    mixins: [FieldComponentMixin],
    events: {
        'calendar:date:selected': function(datetime) {
            let value = moment(this.$els.hidden.value);
            value.year(datetime.year());
            value.month(datetime.month());
            value.date(datetime.date());
            this.$els.hidden.value = value.format();
            return true;
        },
        'calendar:time:selected': function(datetime) {
            let value = moment(this.$els.hidden.value);
            value.hour(datetime.hour());
            value.minute(datetime.minute());
            this.$els.hidden.value = value.format();
            return true;
        }
    }
};
</script>
