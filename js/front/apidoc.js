/**
 * Display a SwaggerUI documentation
 */
import 'front/bootstrap';

import 'less/udata/swagger.less';

import Vue from 'vue';

import $ from 'expose?$!expose?jQuery!jquery';
import commonmark from 'helpers/commonmark';
import hljs from 'hljs';
import log from 'logger';

// Required jQuery plugins
import 'jquery.browser';
import 'swaggerui/lib/jquery.slideto.min';
import 'swaggerui/lib/jquery.wiggle.min';
import 'script!swaggerui/lib/jquery.ba-bbq.min';

import 'expose?Handlebars!handlebars';
import 'script!swaggerui/lib/lodash.min';
import 'script!swaggerui/lib/backbone-min';
import 'script!swaggerui/lib/jsoneditor.min';

import 'script!swaggerui/swagger-ui.min';
SwaggerUi = window.SwaggerUi;

// Marked compatibility for SwaggerUI
window.marked = commonmark;
marked.setOptions = function() {};

// Fix legacy import from Swagger UI
window.hljs = hljs;


new Vue({
    el: 'body',
    ready() {
        hljs.initHighlightingOnLoad();

        const swaggerUi = new SwaggerUi({
            url: $('meta[name="swagger-specs"]').attr('content'),
            dom_id: 'swagger-ui-container',
            supportedSubmitMethods: ['get'],
            onComplete: function(swaggerApi, swaggerUi) {
                log.debug('Loaded SwaggerUI');
            },
            onFailure: function() {
                log.error('Unable to Load SwaggerUI');
            },
            docExpansion: 'none',
            jsonEditor: false,
            defaultModelRendering: 'model',
            validatorUrl: null,
            sorter: 'alpha'
        });

        swaggerUi.load();
    }
});
