import API from 'api';
import moment from 'moment'
import tv4 from 'tv4';
import Vue from 'vue';


for (let key of Object.keys(API.definitions)) {
    let schema = API.definitions[key];
    tv4.addSchema('#/definitions/' + key, schema);
}

tv4.addFormat({
    date: function(data, schema) {
        var m = moment(data, 'YYYY-MM-DD'),
            flags = m.parsingFlags();

        if (!m.isValid() || (flags.unusedInput + flags.unusedTokens).length) {
            return Vue._('Unsupported ISO-8601 date format');
        }
    },
    'date-time': function(data, schema) {
        if (!moment(data, moment.ISO_8601).isValid()) {
            return Vue._('Unsupported ISO-8601 date-time format');
        }
    }
});


export default tv4;
