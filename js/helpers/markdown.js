import markdownit from 'markdown-it';

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
];

const RE_REPLACE_TAGS = new RegExp(`<(\/?(?:${MD_FILTERED_TAGS.join('|')}).*?\/?)>`, 'gi');

const markdown = markdownit({
    html: false,
    linkify: true,
    typographer: true,
    breaks: true,
});

// Disable mail linkification
markdown.linkify.add('mailto:', null)

function escapeRule(tokens, idx, options, env, self) {
    return tokens[idx].content.replace(RE_REPLACE_TAGS, '&lt;$1&gt;');
}

markdown.use(function(md) {
    // Render ~~<text>~~ as del tag
    md.renderer.rules.s_open = function(tokens, idx, options, env, self) {
        const s_open = tokens[idx];
        s_open.type = 'del_open';
        s_open.tag = 'del';
        return self.renderToken(tokens, idx, options);
    };
    md.renderer.rules.s_close = function(tokens, idx, options, env, self) {
        const s_close = tokens[idx];
        s_close.type = 'del_close';
        s_close.tag = 'del';
        return self.renderToken(tokens, idx, options);
    };

    md.renderer.rules.html_block = escapeRule;
    md.renderer.rules.html_inline = escapeRule;
});

export default function(text) {
    return markdown.render(text).trim();
}
