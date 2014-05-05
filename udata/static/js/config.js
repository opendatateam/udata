require.config({
    baseUrl: '/static/js/',
    paths: {
        // Libraries
        'jquery': '../bower/jquery/dist/jquery',
        'bootstrap': '../bower/bootstrap/dist/js/bootstrap',
        'text': "../bower/requirejs-text/text",
        'moment': '../bower/moment/min/moment-with-langs',
        'jquery.validation': '../bower/jquery.validation/jquery.validate',
        'markdown': '../bower/markdown/lib/markdown',
        'bootstrap-markdown': '../bower/bootstrap-markdown/js/bootstrap-markdown',
        'bootstrap-daterangepicker': '../bower/bootstrap-daterangepicker/daterangepicker',
        'selectize': '../bower/selectize/dist/js/standalone/selectize',
        'fineuploader': '../vendor/jquery.fineuploader/jquery.fineuploader',
        'bootstrap-slider': '../bower/seiyria-bootstrap-slider/js/bootstrap-slider',
        'x-editable': '../bower/x-editable/dist/bootstrap3-editable/js/bootstrap-editable',
        'router': '../bower/requirejs-router/router',
        'domReady': '../bower/requirejs-domready/domReady',
        'dotdotdot': '../bower/jquery.dotdotdot/src/js/jquery.dotdotdot' ,

        // To be extracted in extensions
        'd3': '../bower/d3/d3',
        'highstock': '../bower/highstock-components/highstock',

        //Plugins
        'hbs': '../bower/require-handlebars-plugin/hbs',

        // i18n
        'moment-i18n': '../bower/moment/min/langs',

        // Local paths
        'templates': '../templates'
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
        }
    }

    // hbs: { // optional
    //     helpers: true,            // default: true
    //     i18n: false,              // default: false
    //     templateExtension: 'hbs', // default: 'hbs'
    //     partialsUrl: ''           // default: ''
    // }

});
