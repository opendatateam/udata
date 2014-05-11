require.config({
    paths: {
        // Libraries
        'jquery': '../bower/jquery/dist/jquery',
        'bootstrap': '../bower/bootstrap/dist/js/bootstrap',
        'text': "../bower/requirejs-text/text",
        'moment': '../bower/momentjs/min/moment-with-langs',
        'markdown': '../bower/markdown/lib/markdown',
        'bootstrap-markdown': '../bower/bootstrap-markdown/js/bootstrap-markdown',
        'bootstrap-daterangepicker': '../bower/bootstrap-daterangepicker/daterangepicker',
        'selectize': '../bower/selectize/dist/js/standalone/selectize',
        'fineuploader': '../vendor/jquery.fineuploader/jquery.fineuploader',
        'bootstrap-slider': '../bower/seiyria-bootstrap-slider/js/bootstrap-slider',
        'x-editable': '../bower/x-editable/dist/bootstrap3-editable/js/bootstrap-editable',
        'router': '../bower/requirejs-router/router',
        'domReady': '../bower/requirejs-domready/domReady',
        'typeahead': '../bower/typeahead.js/dist/typeahead.jquery',
        'bloodhound': '../bower/typeahead.js/dist/bloodhound',

        // jQuery plugins
        'jquery.microdata': '../bower/jquery.microdata/index',
        'jquery.validation': '../bower/jquery.validation/jquery.validate',
        'dotdotdot': '../bower/jquery.dotdotdot/src/js/jquery.dotdotdot' ,

        // To be extracted in extensions
        'd3': '../bower/d3/d3',
        'highstock': '../bower/highstock-components/highstock',

        //Plugins
        'hbs': '../bower/require-handlebars-plugin/hbs',

        // i18n
        'moment-i18n': '../bower/moment/min/langs',
        'i18next': '../bower/i18next/i18next.amd',

        // Local relative paths
        'templates': '../templates',
        'locales': '../locales'
    },

    shim: {
        'bootstrap': {
            deps: ['jquery'],
            exports: '$.fn.popover'
        },
        'bootstrap-markdown': {
            deps: ['markdown', 'bootstrap'],
            exports: '$.fn.markdown'
        },
        'bootstrap-daterangepicker': {
            deps: ['moment', 'bootstrap'],
            exports: '$.fn.daterangepicker'
        },
        'markdown': {
            exports: 'markdown'
        },
        'jquery.validation': {
            deps: ['jquery'],
            exports: '$.fn.validate'
        },
        'fineuploader': {
            deps: ['jquery'],
            exports: '$.fn.fineUploader'
        },
        'bootstrap-slider': {
            deps: ['jquery'],
            exports: '$.fn.slider'
        },
        'd3': {
            exports: 'd3'
        },
        'highstock': {
            deps: ['jquery'],
            exports: 'StockChart'
        },
        'dotdotdot': {
            deps: ['jquery'],
            exports: '$.fn.dotdotdot'
        },
        'typeahead': {
            deps: ['jquery'],
            exports: '$.fn.typeahead'
        },
        'bloodhound': {
            deps: ['jquery'],
            exports: 'Bloodhound'
        }
    }

    // hbs: { // optional
    //     helpers: true,            // default: true
    //     i18n: false,              // default: false
    //     templateExtension: 'hbs', // default: 'hbs'
    //     partialsUrl: ''           // default: ''
    // }

});
