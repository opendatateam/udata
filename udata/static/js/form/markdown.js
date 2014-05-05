/**
 * Markdown editor widget
 */
define(['jquery', 'bootstrap-markdown'], function($) {
    'use strict';

    // Markdown editor
    $('textarea.md').markdown({
        autofocus: false,
        savable: false
    });

});
