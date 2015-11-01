<style lang="less">
.calendar {
    color: black;

    > * {
        display: block;
    }

    .fa-remove {
        color: red;
    }
}
</style>

<template>
<div class="calendar datepicker" :class="[ 'view' ]">
    <div class="datepicker-{{view}}">
        <table class="table table-condensed">
            <thead>
                <tr>
                    <th class="prev" style="visibility: visible;"
                        @click="previous">«</th>
                    <th colspan="5" class="datepicker-switch"
                        @click="zoomOut">{{rangeDisplay}}</th>
                    <th class="next" style="visibility: visible;"
                        @click="next">»</th>
                </tr>
                <tr v-if="view == 'days'">
                    <th class="dow" v-for="day in days">{{day}}</th>
                </tr>
            </thead>
            <tbody v-show="view == 'days'">
                <tr v-for="week in currentMonthDays">
                    <td class="day"
                        v-for="day in week"
                        @click="pickDay(day)"
                        :class="{
                            'old': isOld(day),
                            'new': isNew(day),
                            'today': day.isSame(today, 'day'),
                            'active': day.isSame(selected, 'day')
                        }">{{ day.date() }}</td>
                </tr>
            </tbody>
            <tbody v-show="view == 'months'">
                <tr>
                    <td colspan="7">
                        <span class="month" v-for="(idx, month) in months"
                            @click="pickMonth(idx)">{{month}}
                        </span>
                    </td>
                </tr>
            </tbody>
            <tbody v-show="view == 'years'">
                <tr>
                    <td colspan="7">
                        <span class="year" v-for="year in yearsRange"
                            @click="pickYear(year)">
                        {{year}}
                        </span>
                    </td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <th colspan="5" @click="pickDay(today)">
                        {{ _('Today') }}
                    </th>
                    <th colspan="2" @click="clear">
                        <span class="fa fa-remove"></span>
                        {{ _('Clear') }}
                    </th>
                </tr>
            </tfoot>
        </table>
    </div>
</div>
</template>

<script>
import moment from 'moment';

const VIEWS = ['days', 'months', 'years'];

export default {
    props: {
        selected: null,
        view: {
            type: String,
            default: 'days'
        }
    },
    data: function() {
        return {
            currentMonth: moment().month(),
            currentYear: moment().year(),
            today: moment()
        };
    },
    computed: {
        days: function() {
            let days = [],
                weekdays = moment.weekdaysShort(),
                first = moment.localeData().firstDayOfWeek();
            for (let i = 0; i < 7; i++) {
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
                let start = moment().year(this.currentYear).subtract(5, 'years'),
                    end = moment().year(this.currentYear).add(6, 'years');
                return start.year() + '-' + end.year();
            }
        },
        currentMonthDays: function() {
            let month = moment().month(this.currentMonth).year(this.currentYear),
                start = month.clone().startOf('month').startOf('week'),
                end = month.clone().endOf('month').endOf('week'),
                days = [], row;

            for (let i=0; i <= end.diff(start, 'days'); i++) {
                if (i % 7 === 0) {
                    row = [];
                    days.push(row);
                }
                row.push(start.clone().add(i, 'days'));
            }
            return days;
        },
        yearsRange: function() {
            let start = moment().year(this.currentYear).subtract(5, 'years'),
                years = [];

            for (let i=0; i < 12; i++) {
                years.push(start.clone().add(i, 'years').year());
            }
            return years;
        }
    },
    methods: {
        next: function() {
            let current = moment().month(this.currentMonth).year(this.currentYear);
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
            let current = moment().month(this.currentMonth).year(this.currentYear);
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
