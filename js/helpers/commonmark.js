import markdownit from 'markdown-it';
import { options } from 'markdown-it/lib/presets/commonmark';


export default function(text) {
    options.linkify = true;
    let markdown = markdownit(options);
    return markdown.render(text);
};
