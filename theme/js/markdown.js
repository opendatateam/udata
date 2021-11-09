import markdownit from 'markdown-it';

const markdown = markdownit({
    html: false,
    linkify: true,
    typographer: true,
    breaks: true,
});

// Disable mail linkification
markdown.linkify.add('mailto:', null)

markdown.use(function(md) {
    md.renderer.rules.link_open = function(tokens, idx, options, env, self) {
        const link_open = tokens[idx];
        link_open.attrs.push(['rel','nofollow']);
        return self.renderToken(tokens, idx, options);
    };
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
});

export default function(text) {
    return markdown.render(text).trim();
}
