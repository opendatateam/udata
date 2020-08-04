/**
 * Serialize a mask as String for header
 * @param  {String|Array} mask The mask to serialize
 * @return {String}      A Serialized mask ready to be used into HTTP header
 */
export function serialize(mask) {
    if (Array.isArray(mask)) {
        return mask.join(',');
    } else if (typeof mask === 'string' || mask instanceof String) {
        return mask;
    } else {
        throw Error('Unsupported mask type');
    }
}

export default serialize;
