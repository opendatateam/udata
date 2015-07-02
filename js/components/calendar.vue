<style lang="less">
.calendar > * {
    display: block;
}
</style>

<template>
<div class="calendar datepicker" v-class="view">
    <div class="datepicker-{{view}}">
        <table class="table table-condensed">
            <thead>
                <tr>
                    <th class="prev" style="visibility: visible;"
                        v-on="click: previous">«</th>
                    <th colspan="5" class="datepicker-switch"
                        v-on="click: zoomOut">{{rangeDisplay}}</th>
                    <th class="next" style="visibility: visible;"
                        v-on="click: next">»</th>
                </tr>
                <tr v-if="view == 'days'">
                    <th class="dow" v-repeat="days">{{$value}}</th>
                </tr>
            </thead>
            <tbody v-show="view == 'days'">
                <tr v-repeat="week:currentMonthDays">
                    <td class="day"
                        v-repeat="day:week"
                        v-on="click: pickDay(day)"
                        v-class="
                            old: isOld(day),
                            new: isNew(day),
                            today: day.isSame(today, 'day'),
                            active: day.isSame(selected, 'day')
                        ">{{ day.date() }}</td>
                </tr>
            </tbody>
            <tbody v-show="view == 'months'">
                <tr>
                    <td colspan="7">
                        <span class="month" v-repeat="months" v-on="click: pickMonth($index)">{{$value}}
                        </span>
                    </td>
                </tr>
            </tbody>
            <tbody v-show="view == 'years'">
                <tr>
                    <td colspan="7">
                        <span class="year" v-repeat="yearsRange" v-on="click: pickYear($value)">
                        {{$value}}
                        </span>
                    </td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <th colspan="7" v-on="click: pickDay(today)">Today</th>
                </tr>
                <tr>
                    <th colspan="7" v-on="click: clear">Clear</th>
                </tr>
            </tfoot>
        </table>
    </div>
</div>
</template>

<script>
'use strict';

var moment = require('moment'),
    VIEWS = ['days', 'months', 'years'];

module.exports = {
    props: ['selected', 'view'],
    computed: {
        days: function() {
            var days = [],
                weekdays = moment.weekdaysShort(),
                first = moment.localeData().firstDayOfWeek();
            for (var i = 0; i < 7; i++) {
                days.push(weekdays[(i + first) % 7]);
            }
            return days;
        },
        months: function() {
            return moment.monthsShort();
        },
        monthDisplay: function() {
            return moment()
                .month(this.currentMonth)
                .year(this.currentYear)
                .format('MMMM YYYY');
        },
        rangeDisplay: function() {
            if (this.view == 'days') {
                return moment()
                    .month(this.currentMonth)
                    .year(this.currentYear)
                    .format('MMMM YYYY');
            } else if (this.view == 'months') {
                return this.currentYear;
            } else if (this.view == 'years') {
                var start = moment().year(this.currentYear).subtract(5, 'years'),
                    end = moment().year(this.currentYear).add(6, 'years');
                return start.year() + '-' + end.year();
            }
        },
        currentMonthDays: function() {
            var month = moment().month(this.currentMonth).year(this.currentYear),
                start = month.clone().startOf('month').startOf('week'),
                end = month.clone().endOf('month').endOf('week'),
                days = [], row;

            for (var i=0; i <= end.diff(start, 'days'); i++) {
                if (i % 7 === 0) {
                    row = [];
                    days.push(row);
                }
                row.push(start.clone().add(i, 'days'));
            }
            return days;
        },
        yearsRange: function() {
            var start = moment().year(this.currentYear).subtract(5, 'years'),
                years = [];

            for (var i=0; i < 12; i++) {
                years.push(start.clone().add(i, 'years').year());
            }
            return years;
        }
    },
    data: function() {
        return {
            currentMonth: moment().month(),
            currentYear: moment().year(),
            today: moment(),
            selected: null,
            view: 'days'
        };
    },
    methods: {
        next: function() {
            var current = moment().month(this.currentMonth).year(this.currentYear);
            if (this.view === 'days') {
                current.add(1, 'months');
            } else if (this.view === 'months') {
                current.add(1, 'years');
            } else if (this.view === 'years') {
                current.add(12, 'years');
            }
            this.currentMonth = current.month();
            this.currentYear = current.year();
        },
        previous: function() {
            var current = moment().month(this.currentMonth).year(this.currentYear);
            if (this.view === 'days') {
                current.subtract(1, 'months');
            } else if (this.view === 'months') {
                current.subtract(1, 'year');
            } else if (this.view === 'years') {
                current.subtract(12, 'years');
            }
            this.currentMonth = current.month();
            this.currentYear = current.year();
        },
        zoomOut: function() {
            if (VIEWS.indexOf(this.view) + 1 < VIEWS.length) {
                this.view = VIEWS[VIEWS.indexOf(this.view) + 1];
            }
        },
        pickDay: function(day) {
            this.selected = day;
            this.$dispatch('calendar:date:selected', day);
        },
        pickMonth: function(month) {
            this.currentMonth = month;
            this.view = 'days';
            this.$dispatch('calendar:month:selected', month);
        },
        pickYear: function(year) {
            this.currentYear = year;
            this.view = 'months';
            this.$dispatch('calendar:year:selected', year);
        },

        isOld: function(date) {
            return date.isBefore(moment().month(this.currentMonth).year(this.currentYear).startOf('month'));
        },

        isNew: function(date) {
            return date.isAfter(moment().month(this.currentMonth).year(this.currentYear).endOf('month'));
        },

        clear: function() {
            this.selected = null;
            this.currentYear = this.today.year();
            this.currentMonth = this.today.month();
            this.view = 'days';
            this.$dispatch('calendar:date:cleared');
        }
    }
};
</script>
