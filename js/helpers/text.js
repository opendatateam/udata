/**
 * Ellipsis a text given a length.
 * @param  {string} text   The text to truncate
 * @param  {int} length The truncate length
 * @return {string}        The truncated text
 */
export function truncate(text, length) {
    if (text && text.length > length) {
        return text.substr(0, length - 1) + '…';
    }
    return text;
}

/**
 * Titleize a string
 * @param  {string} text  The input text to transform
 * @return {string}       The titleized string
 */
export function title(text) {
    return text.replace(/\w\S*/g, txt => {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
}


export const SIZES = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

/**
 * Display a bytes size in a human readable format
 * @param  {int} bytes A file size in baytes
 * @return {String}       The same file size in a human readable unit
 */
export function size(bytes) {
    if (!bytes) return 'n/a';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)), 10);
    const unit = SIZES[i];
    if (i === 0) return `${bytes} ${unit}`;
    const converted = (bytes / Math.pow(1024, i)).toFixed(1);
    return `${converted} ${unit}`;
}

export default {truncate, title, size};
