/**
 * Display a SwaggerUI documentation
 */
'use strict';

require('../less/udata/swagger.less');

var $ = require('expose?$!expose?jQuery!jquery'),
    hljs = require('highlight.js'),
    log = require('logger');

// Required jQuery plugins
require('jquery.browser');
require('swaggerui/lib/jquery.slideto.min');
require('swaggerui/lib/jquery.wiggle.min');
require('script!swaggerui/lib/jquery.ba-bbq.min');

require('expose?Handlebars!handlebars');
require('expose?marked!marked');
require('script!swaggerui/lib/underscore-min');
require('script!swaggerui/lib/backbone-min');

require('script!swaggerui/swagger-ui.min');
SwaggerUi = window.SwaggerUi;

$(function() {
    hljs.initHighlightingOnLoad();
    $('pre code').each(function(i, e) {
        hljs.highlightBlock(e);
    });

    var swaggerUi = new SwaggerUi({
        url: $('meta[name="swagger-specs"]').attr('content'),
        dom_id: "swagger-ui-container",
        supportedSubmitMethods: ['get'],
        onComplete: function(swaggerApi, swaggerUi){
            log.debug("Loaded SwaggerUI");

            $('#swagger-ui-container pre code').each(function(i, e) {
                hljs.highlightBlock(e);
            });
        },
        onFailure: function(data) {
            log.error("Unable to Load SwaggerUI");
        },
        docExpansion: "none",
        sorter: "alpha"
    });

    swaggerUi.load();
});
