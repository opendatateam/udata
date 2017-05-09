<!--
    A component displaying a date range search facet.

    Pickable dates are restricted on the search result range.
    Initial values are extracted from the URL search query.
-->
<template>
<div class="temporal-coverage-facet" v-outside="onOutside">
    <div class="input-group" :class="{ 'open': picking }">
        <input type="text" class="input-sm form-control"
            v-el:start-input :placeholder="_('Start')"
            @focus="onFocus" @input="onChange | debounce 500"
            :required="required"
            :value="currentMin|dt DATE_FORMAT ''">
        <span class="input-group-addon">{{ _('to') }}</span>
        <input type="text" class="input-sm form-control"
            v-el:end-input :placeholder="_('End')"
            @focus="onFocus" @input="onChange | debounce 500"
            :required="required"
            :value="currentMax|dt DATE_FORMAT ''">
    </div>
    <calendar v-ref:calendar v-show="picking" :selected="currentValue" :min="dateMin" :max="dateMax"></calendar>
    <div class="row" v-show="changed && !picking">
        <div class="col-xs-12">
            <button class="btn btn-default btn-block btn-apply" @click="apply">
                <span class="fa fa-refresh"></span>
                {{ _('Apply') }}
            </button>
        </div>
    </div>
</div>
</template>

<script>
import Calendar from 'components/calendar.vue';
import moment from 'moment';

const DATE_FORMAT = 'L';
const ISO_FORMAT = 'YYYY-MM-DD';

export default {
    replace: true,
    components: {Calendar},
    props: {
        min: {
            type: moment,
            coerce: (value) => moment(value),
        },
        max: {
            type: moment,
            coerce: (value) => moment(value),
        },
        name: {
            type: String,
            required: true,
        }
    },
    data() {
        const urlQuery = {min: undefined, max: undefined};
        const search = new URLSearchParams(window.location.search);
        if (search.has(this.name)) {
            const parts = search.get(this.name).split('-');
            if (parts.length === 6) {
                urlQuery.min = moment(parts.slice(0, 3).join('-'));
                urlQuery.max = moment(parts.slice(3, 6).join('-'));
            }
        }
        return {
            picking: false,
            pickedField: null,
            pickedMin: urlQuery.min,
            pickedMax: urlQuery.max,
            urlQuery, DATE_FORMAT
        };
    },
    computed: {
        changed() {
            const minChanged = !this.currentMin.isSame(this.urlQuery.min || this.min);
            const maxChanged = !this.currentMax.isSame(this.urlQuery.max || this.max);
            return minChanged || maxChanged;
        },
        currentValue: {
            get() {
                return this.pickedField === this.$els.startInput ? this.currentMin : this.currentMax;
            },
            set(value) {
                if (this.pickedField === this.$els.startInput) {
                    this.pickedMin = value;
                } else {
                    this.pickedMax = value;
                }
            }
        },
        currentMin() {
            return this.pickedMin || this.min;
        },
        currentMax() {
            return this.pickedMax || this.max;
        },
        dateMin() {
            return this.pickedField === this.$els.endInput ? this.currentMin : this.min;
        },
        dateMax() {
            return this.pickedField === this.$els.startInput ? this.currentMax : this.max;
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
    methods: {
        apply() {
            const filter = `${this.currentMin.format(ISO_FORMAT)}-${this.currentMax.format(ISO_FORMAT)}`;
            const search = new URLSearchParams(window.location.search);
            search.set(this.name, filter);
            window.location.search = search.toString();
        },
        onFocus(e) {
            if (!this.picking || e.target !== this.pickedField) {
                this.$nextTick(this.$refs.calendar.focus);
            }
            this.picking = true;
            this.pickedField = e.target;
        },
        onChange(e) {
            try {
                this.currentValue = moment(e.target.value, DATE_FORMAT);
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

<style lang="less">
.temporal-coverage-facet {
    .calendar, .btn-apply {
        margin-top: 10px;
    }

    input[readonly] {
        cursor: pointer;
        background-color: white;
        text-align: center;
    }
}
</style>
