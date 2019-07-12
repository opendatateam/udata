import markdownit from 'markdown-it';
// import { options, components } from 'markdown-it/lib/presets/commonmark';

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
const MD_FILTERED_TAGS = [
    'title',
    'textarea',
    'style',
    'xmp',
    'iframe',
    'noembed',
    'noframes',
    'script',
    'plaintext',
]

function escapeHtml(html) {
    return html
         .replace(/&/g, '&amp;')
         .replace(/</g, '&lt;')
         .replace(/>/g, '&gt;')
         .replace(/"/g, '&quot;');
        //  .replace(/'/g, '&#039;');
}


/**
 * Sanitize Markdown-it source tags
 * @param  {String} html markdown-it rendered html
 * @return {String}      Sanitized html
 */
function escapeTags(content, config) {
    const fragment = new DOMParser().parseFromString(content, 'text/html');
    const it = document.createNodeIterator(fragment.body, NodeFilter.SHOW_ELEMENT, null, false);
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

const markdown = markdownit({
    html: true,
    linkify: true,
    typographer: true,
    breaks: true,
});

// Disable mail linkification
markdown.linkify.add('mailto:', null)

markdown.use(function(md) {
    const defaultRender = md.renderer.rules.s_open || function(tokens, idx, options, env, self) {
        return self.renderToken(tokens, idx, options);
    };

    md.renderer.rules.s_open = function(tokens, idx, options, env, self) {
        const s_open = tokens[0];
        const s_close = tokens[2];
        s_open.type = 'del_open';
        s_open.tag = 'del';
        s_close.type = 'del_close';
        s_close.tag = 'del';
        return defaultRender(tokens, idx, options, env, self);
    };
});

export default function(text, config) {
    // console.log('text', text)
    // const source = escapeTags(text, config || DEFAULTS);
    // console.log('source', source)
    // // Markdown-it does not removes the "\n" on soft breaks
    // return markdown.render(source).replace(/\n/g, '');
    return markdown.render(text).trim();
}
