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

function nodeToStr(node) {
    const div = document.createElement('div');
    div.appendChild(node.cloneNode(true));
    return div.innerHTML;
}

function escapeTags(content, config) {
    const doc = document.createRange().createContextualFragment(content);
    const it = document.createNodeIterator(doc, NodeFilter.SHOW_ELEMENT);
    let node;

    while (node = it.nextNode()) {
        // Skip p tags and allowed tags
        if (node.nodeName === 'P' || config.tags.indexOf(node.nodeName.toLowerCase()) >= 0) continue;
        const html = nodeToStr(node)
        const escaped = document.createTextNode(escapeHtml(html));
        node.parentNode.replaceChild(escaped, node)
    }

    return nodeToStr(doc);
}

/**
 * Sanitize Markdown-it rendered html
 * @param  {String} html markdown-it rendered html
 * @return {String}      Sanitized html
 */
function sanitize(html, config) {
    // Markdown-it does not removes the "\n" on soft breaks
    html = html.replace(/\n/g, '');
    return escapeTags(html, config);
}

options.linkify = true;
// Enable soft breaks as line returns
options.breaks = true;
const markdown = markdownit().configure({options, components}).enable('linkify');

// Disable mail linkification
markdown.linkify.add('mailto:', null)

export default function(text, config) {
    return sanitize(markdown.render(text), config || DEFAULTS);
}
