define(['tv4', 'moment', 'vue'], function(tv4, moment, Vue) {
    'use strict';

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

    return tv4;
});
