import API from 'api';
import CustomError from 'error';

export class BadgeError extends CustomError {}

/**
 * Known badges
 */
export const TYPES = {
    dataset: 'datasets',
    reuse: 'reuses',
    organization: 'organizations'
};


/**
 * A simple cache for badges
 */
export class Badges {

    /**
     * @param  {Object} types A mapping f(basename) = namespace
     */
    constructor(types) {
        this._badges = {};
        this._types = types;

        // Build a getter for each badges type
        for (const name of Object.keys(types)) {
            this._buildProperty(name);
        }
    }

    _buildProperty(name) {
        Object.defineProperty(this, name, {
            get() {
                if (this._badges.hasOwnProperty(name)) {
                    return this._badges[name];
                }

                const ns = this._types[name];
                const operation = 'available_' + name + '_badges';
                const badges = this._badges[name] = {};

                API.onReady(() => {
                    if (!API.hasOwnProperty(ns) || !API[ns].hasOwnProperty(operation)) {
                        throw new BadgeError(`Badge for "${name}" does not exists`);
                    }

                    API[ns][operation]({}, (response) => {
                        Object.assign(badges, response.obj);
                    });
                })

                return badges;
            }
        });
    }

    /**
     * List available badges for a given object
     * @param  {Object} obj A badgeable object instance
     * @return {Object}     Available badges f(kind) = label
     */
    available(obj) {
        return this[obj.constructor.__badges_type__] || {};
    }

    /**
     * Add a given badge kind to a given object
     * @param {Object}   obj      A badgeable object instance
     * @param {String}   kind     A badge kind code
     * @param {Function} callback An optional callback function(badge)
     */
    add(obj, kind, callback) {
        const data = {payload: {kind: kind}};
        const type = obj.constructor.__badges_type__;
        const key = obj.constructor.__key__ || type;
        const ns = this._types[type];
        const operation = 'add_' + type + '_badge';

        data[key] = obj.id;

        API[ns][operation](data, (response) => {
            obj.badges.push(response.obj);
            if (callback) {
                callback(response.obj);
            }
        });
    }

    /**
     * Remove a given badge kind to a given object
     * @param {Object}   obj      A badgeable object instance
     * @param {String}   kind     A badge kind code
     * @param {Function} callback An optional callback
     */
    remove(obj, kind, callback) {
        const data = {badge_kind: kind};
        const type = obj.constructor.__badges_type__;
        const key = obj.constructor.__key__ || type;
        const ns = this._types[type];
        const operation = 'delete_' + type + '_badge';

        data[key] = obj.id;

        API[ns][operation](data, () => {
            const badge = obj.badges.filter(o => o.kind === kind)[0];
            obj.badges.$remove(badge);
            if (callback) {
                callback();
            }
        });
    }
}

export const badges = new Badges(TYPES);

export default badges;
