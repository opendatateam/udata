import markdownit from 'markdown-it';
import { options, components } from 'markdown-it/lib/presets/commonmark';

const DEFAULTS = {
    tags: [
        'a',
        'abbr',
        'acronym',
        'b',
        'br',
        'blockquote',
        'code',
        'dd',
        'dl',
        'dt',
        'em',
        'i',
        'li',
        'ol',
        'pre',
        'small',
        'strong',
        'ul',
        'sup',
        'sub',
    ]
};

function escapeHtml(html) {
    return html
         .replace(/&/g, '&amp;')
         .replace(/</g, '&lt;')
         .replace(/>/g, '&gt;')
         .replace(/"/g, '&quot;')
         .replace(/'/g, '&#039;');
}


/**
 * Sanitize Markdown-it source tags
 * @param  {String} html markdown-it rendered html
 * @return {String}      Sanitized html
 */
function escapeTags(content, config) {
    const fragment = new DOMParser().parseFromString(content, 'text/html');
    const it = document.createNodeIterator(fragment.body, NodeFilter.SHOW_ELEMENT);
    let node;

    while (node = it.nextNode()) { // eslint-disable-line no-cond-assign
        // Skip body tag and allowed tags
        if (node.nodeName === 'BODY' || config.tags.indexOf(node.nodeName.toLowerCase()) >= 0) continue;
        const html = node.outerHTML;
        const escaped = document.createTextNode(escapeHtml(html));
        node.parentNode.replaceChild(escaped, node);
    }
    return fragment.body.innerHTML;
}

options.linkify = true;
// Enable soft breaks as line returns
options.breaks = true;
const markdown = markdownit().configure({options, components}).enable('linkify');

// Disable mail linkification
markdown.linkify.add('mailto:', null)

export default function(text, config) {
    const source = escapeTags(text, config || DEFAULTS);
    // Markdown-it does not removes the "\n" on soft breaks
    return markdown.render(source).replace(/\n/g, '');
}
