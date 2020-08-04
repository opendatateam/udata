<!-- Markdown editor widget -->
<style lang="less">
@import '~less/udata/markdown';

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
        max-width: 100%;

        .markdown();
    }
}
</style>

<template>
<textarea class="form-control" :rows="field.rows || rows || 6"
    :id="field.id"
    :name="field.id"
    :placeholder="placeholder"
    :required="required"
    :readonly="readonly"
    @input="onChange">{{value || ''}}</textarea>
</template>

<script>
import $ from 'jquery';
import config from 'config';
import {_} from 'i18n';
import {FieldComponentMixin} from 'components/form/base-field';
import markdown from 'helpers/markdown';

const EXCERPT_TOKEN = '<!--- excerpt -->';

require('bootstrap-markdown/js/bootstrap-markdown');

$.fn.markdown.messages[config.lang] = {
    'Bold': _('Bold'),
    'Italic': _('Italic'),
    'Heading': _('Heading'),
    'URL/Link': _('URL/Link'),
    'Image': _('Image'),
    'List': _('List'),
    'Preview': _('Preview'),
    'strong text': _('strong text'),
    'emphasized text': _('emphasized text'),
    'heading text': _('heading text'),
    'enter link description here': _('enter link description here'),
    'Insert Hyperlink': _('Insert Hyperlink'),
    'enter image description here': _('enter image description here'),
    'Insert Image Hyperlink': _('Insert Image Hyperlink'),
    'enter image title here': _('enter image title here'),
    'list text here': _('list text here')
};

export default {
    name: 'markdown-editor',
    props: ['rows'],
    mixins: [FieldComponentMixin],
    ready: function() {
        $(this.$el).markdown({
            language: config.lang,
            autofocus: false,
            savable: false,
            resize: 'both',
            iconlibrary: 'fa',
            onPreview: (e) => markdown(e.getContent()),
            additionalButtons: [
                [{
                    name: 'extras',
                    data: [{
                        name: 'btnSummary',
                        title: _('Summary'),
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
