require.config({
    paths: {
        // Libraries
        'jquery': '../bower/jquery/dist/jquery',
        'bootstrap': '../bower/bootstrap/dist/js/bootstrap',
        'text': "../bower/requirejs-text/text",
        'moment': '../bower/momentjs/min/moment-with-locales',
        'marked': '../bower/marked/lib/marked',
        'bootstrap-markdown': '../bower/bootstrap-markdown/js/bootstrap-markdown',
        'bootstrap-datepicker': '../bower/bootstrap-datepicker/js/bootstrap-datepicker',
        'bootstrap-daterangepicker': '../bower/bootstrap-daterangepicker/daterangepicker',
        'selectize': '../bower/selectize/dist/js/standalone/selectize',
        'fineuploader': '../bower/fineuploader-dist/dist/jquery.fineuploader',
        'bootstrap-slider': '../bower/seiyria-bootstrap-slider/js/bootstrap-slider',
        'x-editable': '../bower/x-editable/dist/bootstrap3-editable/js/bootstrap-editable',
        'router': '../bower/requirejs-router/router',
        'domReady': '../bower/requirejs-domready/domReady',
        'typeahead': '../bower/typeahead.js/dist/typeahead.jquery',
        'bloodhound': '../bower/typeahead.js/dist/bloodhound',
        'highlight': '../bower/highlightjs/highlight.pack',
        'leaflet': '../bower/leaflet/dist/leaflet-src',
        'leaflet.spin': '../bower/leaflet.spin/leaflet.spin',
        'spin': '../bower/spin.js/spin',

        // jQuery plugins
        'jquery.microdata': '../bower/jquery.microdata/index',
        'jquery.validation': '../bower/jquery.validation/dist/jquery.validate',
        'dotdotdot': '../bower/jquery.dotdotdot/src/js/jquery.dotdotdot' ,

        // To be extracted in extensions
        'd3': '../bower/d3/d3',
        'highstock': '../bower/highstock-components/highstock',

        // Swagger based API doc
        'swagger-ui': '../bower/swagger-ui/dist',
        'jquery.browser': '../bower/jquery.browser/dist/jquery.browser',

        //Plugins
        'hbs': '../bower/require-handlebars-plugin/hbs',

        // i18n
        'i18next': '../bower/i18next/i18next.amd',

        // Local relative paths
        'templates': '../templates',
    },

    shim: {
        'bootstrap': {
            deps: ['jquery'],
            exports: '$.fn.popover'
        },
        'bootstrap-markdown': {
            deps: ['marked', 'bootstrap'],
            exports: '$.fn.markdown'
        },
        'bootstrap-datepicker': {
            deps: ['bootstrap'],
            exports: '$.fn.datepicker'
        },
        'bootstrap-daterangepicker': {
            deps: ['moment', 'bootstrap'],
            exports: '$.fn.daterangepicker'
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
        'jquery.microdata': {
            deps: ['jquery'],
            exports: '$.fn.microdata'
        },
        'typeahead': {
            deps: ['jquery'],
            exports: '$.fn.typeahead'
        },
        'bloodhound': {
            deps: ['jquery'],
            exports: 'Bloodhound'
        },
        // Swagger UI
        'swagger-ui/lib/swagger': {
            deps: ['swagger-ui/lib/shred.bundle'],
            exports: 'SwaggerApi'
        },
        'swagger-ui/lib/backbone-min': {
            deps: ['swagger-ui/lib/underscore-min'],
            exports: 'Backbone'
        },
        'highlight': {
            exports: 'hljs'
        },
        'swagger-ui/lib/jquery.ba-bbq.min': {
            deps: ['jquery', 'jquery.browser']
        },
        'swagger-ui/lib/jquery.slideto.min': {
            deps: ['jquery']
        },
        'swagger-ui/lib/jquery.wiggle.min': {
            deps: ['jquery']
        },
        'swagger-ui/swagger-ui': {
            deps: [
                'jquery',
                'swagger-ui/lib/swagger',
                'swagger-ui/lib/handlebars-1.0.0',
                'swagger-ui/lib/underscore-min',
                'swagger-ui/lib/backbone-min',
                'swagger-ui/lib/jquery.ba-bbq.min',
                'swagger-ui/lib/jquery.slideto.min',
                'swagger-ui/lib/jquery.wiggle.min',
                // 'highlight.7.3.pack',
            ],
            exports: 'SwaggerUi'
        }
    },

    hbs: { // optional
        disablei18n: true,              // default: false
    }

});
