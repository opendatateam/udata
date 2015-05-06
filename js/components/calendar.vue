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
                <tr>
                    <td class="old day">25</td>
                    <td class="old day">26</td>
                    <td class="old day">27</td>
                    <td class="old day">28</td>
                    <td class="old day">29</td>
                    <td class="old day">30</td>
                    <td class="old day">31</td>
                </tr>
                <tr>
                    <td class="day">1</td>
                    <td class="day">2</td>
                    <td class="day">3</td>
                    <td class="day">4</td>
                    <td class="day">5</td>
                    <td class="day">6</td>
                    <td class="day">7</td>
                </tr>
                <tr>
                    <td class="day">8</td>
                    <td class="day">9</td>
                    <td class="day">10</td>
                    <td class="day">11</td>
                    <td class="day">12</td>
                    <td class="day">13</td>
                    <td class="day">14</td>
                </tr>
                <tr>
                    <td class="day">15</td>
                    <td class="day">16</td>
                    <td class="day">17</td>
                    <td class="day">18</td>
                    <td class="day">19</td>
                    <td class="day">20</td>
                    <td class="day">21</td>
                </tr>
                <tr>
                    <td class="day">22</td>
                    <td class="day">23</td>
                    <td class="day">24</td>
                    <td class="day">25</td>
                    <td class="day">26</td>
                    <td class="day">27</td>
                    <td class="day">28</td>
                </tr>
                <tr>
                    <td class="new day">1</td>
                    <td class="new day">2</td>
                    <td class="new day">3</td>
                    <td class="new day">4</td>
                    <td class="new day">5</td>
                    <td class="new day">6</td>
                    <td class="new day">7</td>
                </tr>
            </tbody>
            <tbody v-show="view == 'months'">
                <tr>
                    <td colspan="7">
                        <span class="month" v-repeat="months">{{$value}}</span>
                    </td>
                </tr>
            </tbody>
            <tbody v-show="view == 'years'">
                <tr>
                    <td colspan="7">
                        <span class="year" v-repeat="yearsRange">{{$value}}</span>
                        <!--span class="year old">2009</span>
                        <span class="year">2010</span>
                        <span class="year">2011</span>
                        <span class="year">2012</span>
                        <span class="year">2013</span>
                        <span class="year">2014</span>
                        <span class="year">2015</span>
                        <span class="year">2016</span>
                        <span class="year">2017</span>
                        <span class="year">2018</span>
                        <span class="year">2019</span>
                        <span class="year new">2020</span-->
                    </td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <th colspan="7" class="today" style="display: none;">Today</th>
                </tr>
                <tr>
                    <th colspan="7" class="clear" style="display: none;">Clear</th>
                </tr>
            </tfoot>
        </table>
    </div>
    <!--div class="datepicker-months" v-show="view === 'months'">
        <table class="table table-condensed">
            <thead>
                <tr>
                    <th class="prev" style="visibility: visible;">«</th>
                    <th colspan="5" class="datepicker-switch">2015</th>
                    <th class="next" style="visibility: visible;">»</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="7">
                        <span class="month" v-repeat="months">{{$value}}</span>
                    </td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <th colspan="7" class="today" style="display: none;">Today</th>
                </tr>
                <tr>
                    <th colspan="7" class="clear" style="display: none;">Clear</th>
                </tr>
            </tfoot>
        </table>
    </div>
    <div class="datepicker-years" v-show="view === 'years'">
        <table class="table table-condensed">
            <thead>
                <tr>
                    <th class="prev" style="visibility: visible;">«</th>
                    <th colspan="5" class="datepicker-switch">2010-2019</th>
                    <th class="next" style="visibility: visible;">»</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td colspan="7">
                        <span class="year old">2009</span>
                        <span class="year">2010</span>
                        <span class="year">2011</span>
                        <span class="year">2012</span>
                        <span class="year">2013</span>
                        <span class="year">2014</span>
                        <span class="year">2015</span>
                        <span class="year">2016</span>
                        <span class="year">2017</span>
                        <span class="year">2018</span>
                        <span class="year">2019</span>
                        <span class="year new">2020</span>
                    </td>
                </tr>
            </tbody>
            <tfoot>
                <tr>
                    <th colspan="7" class="today" style="display: none;">Today</th>
                </tr>
                <tr>
                    <th colspan="7" class="clear" style="display: none;">Clear</th>
                </tr>
            </tfoot>
        </table>
        </div-->
    </div>
</template>

<script>
'use strict';

var moment = require('moment'),
    VIEWS = ['days', 'months', 'years'];

module.exports = {
    computed: {
        days: function() {
            return moment.weekdaysShort();
        },
        months: function() {
            return moment.monthsShort();
        },
        monthDisplay: function() {
            return moment().month(this.currentMonth).year(this.currentYear).format('MMMM YYYY');
        },
        rangeDisplay: function() {
            if (this.view == 'days') {
                return moment().month(this.currentMonth).year(this.currentYear).format('MMMM YYYY');
            } else if (this.view == 'months') {
                return this.currentYear;
                // moment().month(this.currentMonth).year(this.currentYear).format('YYYY');
            } else if (this.view == 'years') {
                var start = moment().year(this.currentYear).subtract(5, 'years'),
                    end = moment().year(this.currentYear).add(6, 'years');
                return start.year() + '-' + end.year();
            }
        },
        currentMonthDays: function() {

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
            selected: moment(),
            view: 'days'
        };
    },
    ready: function() {
        // debugger;
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
            console.log('zoomout', this.view, VIEWS.indexOf(this.view), VIEWS.length);
            if (VIEWS.indexOf(this.view) <= VIEWS.length) {
                this.view = VIEWS[VIEWS.indexOf(this.view) + 1];
            }
        },
        pickDay: function(day) {

        },
        pickMonth: function(month) {

        },
        pickYear: function(year) {

        }
    }
};
</script>
