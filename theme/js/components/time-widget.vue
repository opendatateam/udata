<style lang="less">
.datepicker {
    padding: 0 4px;

    > div {
        display: block;
    }

    .close {
        clear: both;
    }
}
</style>

<template>
<div class="calendar datepicker" :class="[ 'view' ]">
    <div class="btn-group btn-group-sm btn-group-justified" role="group">
      <div class="btn-group" role="group">
        <button @click="pickBefore" type="button" class="btn btn-default">{{ _('- 1h') }}</button>
      </div>
      <div class="btn-group" role="group">
        <button @click="pickNow" type="button" class="btn btn-default">{{ _('Now') }}</button>
      </div>
      <div class="btn-group" role="group">
        <button @click="pickAfter" type="button" class="btn btn-default">{{ _('+ 1h') }}</button>
      </div>
    </div>
    <button @click="close" type="button" class="close" aria-label="Close"><span aria-hidden="true">&times;</span></button>
</div>
</template>

<script>
import moment from 'moment';

export default {
    props: ['selected'],
    data: function() {
        return {
            currentHour: null,
            currentMinute: null,
            selected: true
        };
    },
    ready: function() {
        this.currentHour = moment(this.selected).hour();
        this.currentMinute = moment(this.selected).minute();
    },
    methods: {
        pickNow: function() {
            let current = moment();
            this.currentHour = current.hour();
            this.currentMinute = current.minute();
            this.$dispatch('calendar:time:selected', current);
        },

        pickBefore: function() {
            let current = moment().hour(this.currentHour).minute(this.currentMinute);
            current.subtract(1, 'hour');
            this.currentHour = current.hour();
            this.currentMinute = current.minute();
            this.$dispatch('calendar:time:selected', current);
        },

        pickAfter: function() {
            let current = moment().hour(this.currentHour).minute(this.currentMinute);
            current.add(1, 'hour');
            this.currentHour = current.hour();
            this.currentMinute = current.minute();
            this.$dispatch('calendar:time:selected', current);
        },

        close: function() {
            this.$dispatch('calendar:time:close');
        }
    }
};
</script>
