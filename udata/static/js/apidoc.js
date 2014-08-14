/**
 * Common stack, plugins and helpers
 */
define([
    'jquery',
    // 'swagger-ui/lib/swagger',
    'swagger-ui/swagger-ui',
    'swagger-ui/lib/highlight.7.3.pack',
    'logger'
], function($, SwaggerUi, hljs, log) {
    'use strict';

    return {
        start: function() {
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
                        hljs.highlightBlock(e)
                    });
                },
                onFailure: function(data) {
                    log.error("Unable to Load SwaggerUI");
                },
                docExpansion: "list",
                sorter: "alpha"
            });

            window.swaggerUi.load();
        }
    };

});
