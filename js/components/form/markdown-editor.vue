<!-- Markdown editor widget -->
<style lang="less">
@padding: 6px 12px;

.md-editor {
     > textarea {
        background: white;
        padding: @padding;
        border-bottom: none;
    }

    &.active {
        border-color: #3c8dbc;
        -webkit-box-shadow: none;
                box-shadow: none;

    }

    .form-group.has-error & {
        border-color: #dd4b39;
    }

    .form-group.has-success & {
        border-color: #00a65a;
    }

    .btn {
        border-radius: 0;

        &.btn-default {
            background-color: white;
        }
    }

    .md-preview {
        color: black;
        padding: @padding;
    }
}
</style>

<template>
<textarea class="form-control" :rows="rows || 6"
    :id="field.id"
    :name="field.id"
    :placeholder="placeholder"
    :required="required"
    :readonly="readonly">{{value || ''}}</textarea>
</template>

<script>
import $ from 'jquery';
import Vue from 'vue';
import {FieldComponentMixin} from 'components/form/base-field';

const EXCERPT_TOKEN = '<!--- excerpt -->';

window.marked = require('marked');
require('bootstrap-markdown/js/bootstrap-markdown');

$.fn.markdown.messages[Vue.lang] = {
    'Bold': Vue._('Bold'),
    'Italic': Vue._('Italic'),
    'Heading': Vue._('Heading'),
    'URL/Link': Vue._('URL/Link'),
    'Image': Vue._('Image'),
    'List': Vue._('List'),
    'Preview': Vue._('Preview'),
    'strong text': Vue._('strong text'),
    'emphasized text': Vue._('emphasized text'),
    'heading text': Vue._('heading text'),
    'enter link description here': Vue._('enter link description here'),
    'Insert Hyperlink': Vue._('Insert Hyperlink'),
    'enter image description here': Vue._('enter image description here'),
    'Insert Image Hyperlink': Vue._('Insert Image Hyperlink'),
    'enter image title here': Vue._('enter image title here'),
    'list text here': Vue._('list text here')
};

export default {
    name: 'markdown-editor',
    replace: true,
    props: ['rows'],
    mixins: [FieldComponentMixin],
    ready: function() {
        $(this.$el).markdown({
            language: Vue.lang,
            autofocus: false,
            savable: false,
            resize: 'both',
            iconlibrary: 'fa',
            additionalButtons: [
                [{
                    name: 'extras',
                    data: [{
                        name: 'btnSummary',
                        title: Vue._('Summary'),
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
    }
};
</script>
