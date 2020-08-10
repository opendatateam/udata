/*
 * Shim Highlight JS to only include need syntax highlighting and avoid compilation errors
 */
import hljs from '../node_modules/highlight.js/lib/highlight';

// Only inlude needed syntax. New syntax should be added here
hljs.registerLanguage('bash', require(`highlight.js/lib/languages/bash`));
hljs.registerLanguage('http', require(`highlight.js/lib/languages/http`));
hljs.registerLanguage('json', require(`highlight.js/lib/languages/json`));

export default hljs;
