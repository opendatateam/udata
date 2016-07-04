import API from 'api';
import moment from 'moment';
import tv4 from 'tv4';
import Vue from 'vue';

API.onReady(function() {
    for (const key of Object.keys(API.definitions)) {
        const schema = API.definitions[key];
        tv4.addSchema('#/definitions/' + key, schema);
    }
});


tv4.addFormat({
    date: function(data) {
        const m = moment(data, 'YYYY-MM-DD');
        const flags = m.parsingFlags();

        if (!m.isValid() || (flags.unusedInput + flags.unusedTokens).length) {
            return Vue._('Unsupported ISO-8601 date format');
        }
    },
    'date-time': function(data) {
        if (!moment(data, moment.ISO_8601).isValid()) {
            return Vue._('Unsupported ISO-8601 date-time format');
        }
    }
});


export default tv4;
