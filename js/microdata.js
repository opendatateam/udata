/*
 * A Microdata parser nd extractor
 * Inspired by https://github.com/nathan7/microdata
 */

/**
 * Lookups attributes mapping
 */
const LOOKUPS = {
    '*': 'textContent',
    meta: 'content',
    audio: 'src',
    embed: 'src',
    iframe: 'src',
    img: 'src',
    source: 'src',
    video: 'src',
    a: 'href',
    area: 'href',
    link: 'href',
    object: 'data',
    time: 'datetime',
};


/**
 * Extract microdata metadata from a given element
 * @param  {HTMLElement} root   The root element to parse microdata from
 * @return {Object}             The extracted microdata metadata
 */
function extract(root) {
    const obj = {
        $type: root.getAttribute('itemtype'),
        $el: root,
    };
    let children = [...root.children];

    if (root.hasAttribute('itemid')) {
        obj.id = root.getAttribute('itemid');
    }

    while (children.length) {
        const el = children.shift();
        const itemprop = el.getAttribute('itemprop');
        if (itemprop) {
            add(obj, itemprop, value(el));
        }
        if (!el.hasAttribute('itemscope') && el.children.length) {
            children = [...el.children, ...children];
        }
    }
    return obj;
}


/**
 * Match  and extract microdata of a given itemtype.
 * @param  {String} itemtype    The itemtype URL
 * @param  {HTMLElement} el     An optionnal root element to restrict the search to
 * @return {Array}              A list of extracted object
 */
function microdata(itemtype, el) {
    el = el || document;
    const els = el.querySelectorAll(`[itemscope][itemtype="${itemtype}"]`);
    return [...els].map(function(el) {
        return extract(el);
    });
}

microdata.extract = extract;


/**
 * Add a metadata to an object.
 * Transform it into an Array when necessary.
 * @param {Object} obj the target metadata container
 * @param {String} key The metadata name
 * @param {Object} val The metadata value
 */
function add(obj, key, val) {
    if (val === null) return;

    const prop = obj[key];
    if (!prop) {
        obj[key] = val;
    } else {
        if (Array.isArray(prop)) prop.push(val);
        else obj[key] = [prop, val];
    }
}

/**
 * Extract microdata metadata from an element attribute.
 *
 * The looked up attribute depends of the element type.
 * If the element is a new itemscope, an Object is extracted
 * @param  {HTMLElement} el The element to extract the metadata value from
 * @return {Object}         The extracted value
 */
function value(el) {
    if (el.hasAttribute('itemscope')) return extract(el);
    const attr = LOOKUPS[el.tagName.toLowerCase()] || LOOKUPS['*'];
    return el[attr] || el.getAttribute(attr);
}

export default microdata;
