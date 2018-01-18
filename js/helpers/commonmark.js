import markdownit from 'markdown-it';
import { options, components } from 'markdown-it/lib/presets/commonmark';

options.linkify = true;
const markdown = markdownit().configure({options, components}).enable('linkify');

export default function(text) {
    return markdown.render(text);
}
