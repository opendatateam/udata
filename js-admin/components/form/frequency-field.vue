<style lang="less">
.frequency-field {
    width: 100%;

    .date-picker {
        float: right;
        width: 23%;
    }
    .select-input {
        width: 75%;
    }
}
</style>

<template>
<div class="input-group dropdown frequency-field">
    <date-picker field="{{ frequency_date_field }}" value="" v-ref="picker"></date-picker>
    <select-input choices="{{ choices }}" v-on="change: onSelect()" class="select-input" v-ref="select"></select-input>
</div>
</template>

<script>
import moment from 'moment';

const DEFAULT_FORMAT = 'L';
const ISO_FORMAT = 'YYYY-MM-DDTHH:mm:ss';

export default {
    name: 'frequency-field',
    inherit: true,
    replace: true,
    data: function() {
        return {
            placeholder: this._('Expected update')
        };
    },
    computed: {
        frequency_date_field: function() {
            return {
                id: this.field.frequency_date_id
            };
        }
    },
    methods: {
        onSelect: function() {
            let value = this.$.select.$el.value;
            let dateInput = this.$.picker.$$.input;
            let dateHidden = this.$.picker.$$.hidden;
            let futureDate = '';
            switch (value) {
                case "daily":
                    futureDate = moment().add(1, "days");
                    break;
                case "weekly":
                    futureDate = moment().add(1, "weeks");
                    break;
                case "fortnighly":
                    futureDate = moment().add(2, "weeks");
                    break;
                case "monthly":
                    futureDate = moment().add(1, "months");
                    break;
                case "bimonthly":
                    futureDate = moment().add(2, "months");
                    break;
                case "quarterly":
                    futureDate = moment().add(3, "months");
                    break;
                case "biannual":
                    futureDate = moment().add(6, "months");
                    break;
                case "annual":
                    futureDate = moment().add(1, "years");
                    break;
                case "biennial":
                    futureDate = moment().add(2, "years");
                    break;
                case "triennial":
                    futureDate = moment().add(3, "years");
                    break;
                case "quinquennial":
                    futureDate = moment().add(5, "years");
                    break;
                case "unknown":
                case "punctual":
                case "realtime":
                default:
                    futureDate = '';
            }
            dateInput.value = futureDate ? futureDate.format(DEFAULT_FORMAT) : "";
            dateHidden.value = futureDate ? futureDate.format(ISO_FORMAT) : "";
        }
    }
};
</script>
