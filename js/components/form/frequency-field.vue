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
    <date-picker v-ref:picker :field="frequency_date_field"
        :value="frequency_date_value" :placeholder="_('Last update')">
    </date-picker>
    <select-input v-ref:select :choices="choices" @change="onSelect()"
        class="select-input" :field="field" :model="model"
        :schema="schema" :property="property" :value="value"
        :description="description" :placeholder="placeholder"
        :required="required">
    </select-input>
</div>
</template>

<script>
import moment from 'moment';
import {FieldComponentMixin} from 'components/form/base-field';

const DEFAULT_FORMAT = 'L';
const ISO_FORMAT = 'YYYY-MM-DDTHH:mm:ss';

export default {
    name: 'frequency-field',
    replace: true,
    mixins: [FieldComponentMixin],
    props: {
        placeholder: {
            type: String,
            default: function() {return this._('Expected update');}
        }
    },
    components: {
        'date-picker': require('components/form/date-picker.vue'),
        'select-input': require('components/form/select-input.vue')
    },
    computed: {
        frequency_date_field: function() {
            return {
                id: this.field.frequency_date_id
            };
        },
        frequency_date_value: function() {
            return this.model[this.field.frequency_date_id] || '';
        }
    },
    methods: {
        onSelect: function() {
            let value = this.$refs.select.$el.value;
            let dateInput = this.$refs.picker.$els.input;
            let dateHidden = this.$refs.picker.$els.hidden;
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
