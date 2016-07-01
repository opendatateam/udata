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
import 'script!swaggerui/lib/underscore-min';
import 'script!swaggerui/lib/backbone-min';
import 'script!swaggerui/lib/jsoneditor.min';

import 'script!swaggerui/swagger-ui.min';
SwaggerUi = window.SwaggerUi;

// Marked compatibility for SwaggerUI
window.marked = commonmark;
marked.setOptions = function() {};


new Vue({
    el: 'body',
    ready() {
        hljs.initHighlightingOnLoad();
        $('pre code').each(function(i, e) {
            hljs.highlightBlock(e);
        });

        const swaggerUi = new SwaggerUi({
            url: $('meta[name="swagger-specs"]').attr('content'),
            dom_id: 'swagger-ui-container',
            supportedSubmitMethods: ['get'],
            onComplete: function(swaggerApi, swaggerUi) {
                log.debug('Loaded SwaggerUI');

                $('#swagger-ui-container pre code').each(function(i, e) {
                    hljs.highlightBlock(e);
                });
            },
            onFailure: function() {
                log.error('Unable to Load SwaggerUI');
            },
            docExpansion: 'none',
            // jsonEditor: true,
            sorter: 'alpha'
        });

        swaggerUi.load();
    }
});
