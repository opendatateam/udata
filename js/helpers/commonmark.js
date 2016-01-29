import markdownit from 'markdown-it';
import { options } from 'markdown-it/lib/presets/commonmark';

options.linkify = true;
const markdown = markdownit(options);

export default function(text) {
    return markdown.render(text);
}
