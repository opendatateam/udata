/**
 * Markdown editor widget
 */
define([
    'jquery',
    'i18n',
    'helpers/commonmark',
    'bootstrap-markdown/js/bootstrap-markdown'
], function($, i18n, commonmark) {
    'use strict';

    var EXCERPT_TOKEN = '<!--- excerpt -->';

    $.fn.markdown.messages[i18n.lang] = {
        'Bold': i18n._('Bold'),
        'Italic': i18n._('Italic'),
        'Heading': i18n._('Heading'),
        'URL/Link': i18n._('URL/Link'),
        'Image': i18n._('Image'),
        'List': i18n._('List'),
        'Preview': i18n._('Preview'),
        'strong text': i18n._('strong text'),
        'emphasized text': i18n._('emphasized text'),
        'heading text': i18n._('heading text'),
        'enter link description here': i18n._('enter link description here'),
        'Insert Hyperlink': i18n._('Insert Hyperlink'),
        'enter image description here': i18n._('enter image description here'),
        'Insert Image Hyperlink': i18n._('Insert Image Hyperlink'),
        'enter image title here': i18n._('enter image title here'),
        'list text here': i18n._('list text here')
    };

    // Markdown editor
    $('textarea.md').markdown({
        language: i18n.lang,
        autofocus: false,
        savable: false,
        resize: 'both',
        iconlibrary: 'fa',
        onPreview: (e) => commonmark(e.getContent()),
        additionalButtons: [
            [{
                name: 'extras',
                data: [{
                    name: 'btnSummary',
                    title: i18n._('Summary'),
                    icon: 'fa fa-scissors',
                    callback: function(e){
                        var selected = e.getSelection(),
                            cursor = selected.start;

                        e.replaceSelection(EXCERPT_TOKEN);
                        e.setSelection(cursor, cursor + EXCERPT_TOKEN.length);
                    }
                }]
            }]
        ]
    });

});
