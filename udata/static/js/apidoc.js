/**
 * Display a SwaggerUI documentation
 */
define([
    'jquery',
    'swagger-ui/swagger-ui',
    'highlight',
    'logger'
], function($, SwaggerUi, hljs, log) {
    'use strict';

    return {
        start: function() {
            hljs.initHighlightingOnLoad();
            window.swaggerUi = new SwaggerUi({
                url: $('meta[name="swagger-specs"]').attr('content'),
                dom_id: "swagger-ui-container",
                supportedSubmitMethods: ['get', 'post', 'put', 'delete'],
                onComplete: function(swaggerApi, swaggerUi){
                    log.debug("Loaded SwaggerUI");

                    // if(typeof initOAuth == "function") {

                    //     initOAuth({
                    //       clientId: "your-client-id",
                    //       realm: "your-realms",
                    //       appName: "your-app-name"
                    //     });

                    // }
                    $('pre code').each(function(i, e) {
                        hljs.highlightBlock(e);
                    });
                },
                onFailure: function(data) {
                    log.error("Unable to Load SwaggerUI");
                },
                docExpansion: "none",
                sorter: "alpha"
            });

            window.swaggerUi.load();
        }
    };

});
