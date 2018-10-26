<template>
<div class="calendar" :class="[ 'view' ]">
    <div class="calendar-{{view}}">
        <nav>
            <button class="prev" @click.prevent="previous" :disabled="previousDisabled">
                <span class="fa fa-chevron-left"></span>
            </button>
            <button class="switch" @click.prevent="zoomOut">{{ rangeDisplay }}</button>
            <button class="next" @click.prevent="next" :disabled="nextDisabled">
                <span class="fa fa-chevron-right"></span>
            </button>
        </nav>
        <main v-if="view == 'days'" class="days">
            <header>
                <span class="dow" v-for="day in days">{{ day }}</span>
            </header>
            <div v-for="week in monthDays(current)">
                <button v-for="day in week" class="day" :class="dayClasses(day)"
                    @click.prevent="pickDay(day)" :disabled="isDisabled(day)">
                    {{ day.date() }}
                </button>
            </div>
        </main>
        <main v-if="view == 'months'" class="months">
            <button v-for="(idx, month) in months" class="month" @click.prevent="pickMonth(idx)"
                :disabled="isMonthDisabled(idx)">
                {{ month }}
            </button>
        </main>
        <main v-if="view == 'years'" class="years">
            <button v-for="year in yearsRange" class="year" @click.prevent="pickYear(year)"
                :disabled="isYearDisabled(year)">
                {{ year }}
            </button>
        </main>
        <footer>
            <button @click.prevent="pickDay(today)">{{ _('Today') }}</button>
            <button @click.prevent="clear">
                <span class="fa fa-remove"></span>
                {{ _('Clear') }}
            </button>
        </footer>
    </div>
</div>
</template>

<script>
import moment from 'moment';

const VIEWS = ['days', 'months', 'years'];
const MONTH_FORMAT = 'MMMM YYYY';

function optionalMoment(value) {
    return value ? moment(value) : null
}

export default {
    name: 'calendar',
    props: {
        selected: {
            type: moment,
            coerce: optionalMoment,
            default: null,
        },
        min: {
            type: moment,
            coerce: optionalMoment,
            default: null,
        },
        max: {
            type: moment,
            coerce: optionalMoment,
            default: null,
        },
        view: {
            type: String,
            default: 'days'
        }
    },
    data() {
        const current = this.selected || moment();
        return {
            current: current,
            today: moment()
        };
    },
    computed: {
        days() {
            const days = [];
            const weekdays = moment.weekdaysMin();
            const first = moment.localeData().firstDayOfWeek();
            for (let i = 0; i < 7; i++) {
                days.push(weekdays[(i + first) % 7]);
            }
            return days;
        },
        months() {
            return moment.monthsShort();
        },
        monthDisplay() {
            return this.current.format(MONTH_FORMAT);
        },
        rangeDisplay() {
            if (this.view == 'days') {
                return this.current.format(MONTH_FORMAT);
            } else if (this.view == 'months') {
                return this.current.year();
            } else if (this.view == 'years') {
                const start = this.current.clone().subtract(5, 'years');
                const end = this.current.clone().add(6, 'years');
                return `${start.year()}-${end.year()}`;
            }
        },
        yearsRange() {
            const start = this.current.clone().subtract(5, 'years');
            const years = [];

            for (let i=0; i < 12; i++) {
                years.push(start.clone().add(i, 'years').year());
            }
            return years;
        },
        nextValue() {
            const value = this.current.clone();
            if (this.view === 'days') {
                value.add(1, 'months');
            } else if (this.view === 'months') {
                value.add(1, 'years');
            } else if (this.view === 'years') {
                value.add(12, 'years');
            }
            return value;
        },
        previousValue() {
            const value = this.current.clone();
            if (this.view === 'days') {
                value.subtract(1, 'months');
            } else if (this.view === 'months') {
                value.subtract(1, 'year');
            } else if (this.view === 'years') {
                value.subtract(12, 'years');
            }
            return value;
        },
        nextDisabled() {
            if (!this.max) return;
            switch (this.view) {
                case 'days': return this.nextValue.isAfter(this.max, 'month');
                case 'months': return this.nextValue.isAfter(this.max, 'year');
                case 'years': return this.yearsRange.slice(-1).pop() >= this.max.year();
            }
        },
        previousDisabled() {
            if (!this.min) return;
            switch (this.view) {
                case 'days': return this.previousValue.isBefore(this.min, 'month');
                case 'months': return this.previousValue.isBefore(this.min, 'year');
                case 'years': return this.yearsRange[0] <= this.min.year();
            }
        }
    },
    methods: {
        monthDays(date) {
            const start = date.clone().startOf('month').startOf('week');
            const end = date.clone().endOf('month').endOf('week');
            const days = [];
            let row;

            for (let i=0; i <= end.diff(start, 'days'); i++) {
                if (i % 7 === 0) {
                    row = [];
                    days.push(row);
                }
                row.push(start.clone().add(i, 'days'));
            }
            return days;
        },
        next() {
            this.current = this.nextValue;
        },
        previous() {
            this.current = this.previousValue;
        },
        zoomOut() {
            if (VIEWS.indexOf(this.view) + 1 < VIEWS.length) {
                this.view = VIEWS[VIEWS.indexOf(this.view) + 1];
            }
        },
        pickDay(day) {
            this.selected = day;
            this.$dispatch('calendar:date:selected', day);
        },
        pickMonth(month) {
            this.current = this.current.month(month);
            this.view = 'days';
            this.$dispatch('calendar:month:selected', month);
        },
        pickYear(year) {
            this.current = this.current.year(year);
            this.view = 'months';
            this.$dispatch('calendar:year:selected', year);
        },

        isOld(day) {
            return day.isBefore(this.current.startOf('month'));
        },

        isNew(day) {
            return day.isAfter(this.current.endOf('month'));
        },

        isDisabled(day) {
            const isBeforeMin = this.min && day.isBefore(this.min, 'day');
            const isAfterMax = this.max && day.isAfter(this.max, 'day');
            return isBeforeMin || isAfterMax;
        },

        isMonthDisabled(idx) {
            const month = this.current.clone().month(idx);
            const isBeforeMin = this.min && month.isBefore(this.min, 'month');
            const isAfterMax = this.max && month.isAfter(this.max, 'month');
            return isBeforeMin || isAfterMax;
        },

        isYearDisabled(year) {
            const isBeforeMin = this.min && year < this.min.year();
            const isAfterMax = this.max && year > this.max.year();
            return isBeforeMin || isAfterMax;
        },

        dayClasses(day) {
            return {
                old: this.isOld(day),
                new: this.isNew(day),
                today: day.isSame(this.today, 'day'),
                active: day.isSame(this.selected, 'day')
            };
        },

        focus() {
            // Focus active or first button
            const button = this.$el.querySelector('main button.active:not(:disabled)')
                || this.$el.querySelector('main button:not(:disabled)');
            if (button) button.focus();
        },

        clear() {
            this.selected = null;
            this.current = this.today.clone();
            this.view = 'days';
            this.$dispatch('calendar:date:cleared');
        }
    },
    watch: {
        selected(value) {
            if (!value) return;
            this.current = value.clone();
        }
    }
};
</script>

<style lang="less">
// Needs to chose between udata and admin variables
// Choice might happen after the core/admin split
@import '~bootstrap/less/variables';
@import '~bootstrap/less/mixins';

.calendar {
    @unit: 30px;
    color: black;

    min-width: 7 * @unit;

    > * {
        display: block;
    }

    .fa-remove {
        color: red;
    }

    border-radius: @border-radius-base;

    nav {
        font-weight: bold;
        display: flex;

        .switch {
            flex: 2 0 50%;
        }

        .prev, .next {
            flex: 1;
        }
    }

    main {
        display: flex;
        flex-wrap: wrap;


        header {
            font-weight: bold;
            span {
                height: @unit;
                padding-top: 10px;
                line-height: 20px;
            }
        }

        &.days {
            > * {
                display: flex;
                flex: 1 0 100%;
            }

            span, button {
                flex: 1 0 @unit;
                text-align: center;
            }
        }

        &.months, &.years {
            flex-wrap: wrap;
            button {
                flex: 1 0 25%;
                text-align: center;
                height: 54px;
                line-height: 54px;
            }
        }
    }

    footer {
        font-weight: bold;
        display: flex;
    }

    button {
        height: @unit;
        width: 100%;
        background: none;
        border: none;
        border-radius: @border-radius-base;

        &:hover {
            background: @gray-lighter;
        }

        &.old,
        &.new {
            color: @btn-link-disabled-color;
        }

        &.day:hover,
        &:focus {
            background: @gray-lighter;
            cursor: pointer;
        }

        &:disabled,
        &:disabled:hover {
            background: none;
            color: @btn-link-disabled-color;
            cursor: not-allowed;
        }

        &.today {
            @today-bg: lighten(orange, 30%);
            @today-color: #000;
            .button-variant(@today-color, @today-bg, darken(@today-bg, 20%));
            position: relative;

            &:focus {
                background: darken(@today-bg, 10%);
            }

            &:disabled,
            &:disabled:active {
                background: @today-bg;
                color: @btn-link-disabled-color;
            }

            &:before {
                content: '';
                display: inline-block;
                border: solid transparent;
                border-width: 0 0 7px 7px;
                border-bottom-color: @today-color;
                border-top-color: @today-bg;
                position: absolute;
                bottom: 4px;
                right: 4px;
            }
        }

        &.active {
            .button-variant(@btn-primary-color, @btn-primary-bg, @btn-primary-border);
            text-shadow: 0 -1px 0 rgba(0,0,0,.25);

            &.today:before {
                border-bottom-color: @btn-primary-color;
            }
        }
    }
}
</style>
