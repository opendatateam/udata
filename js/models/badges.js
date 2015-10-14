import API from 'api';
import BaseError from 'models/error';

export class BadgeError extends BaseError {};

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
        for (let name of Object.keys(types)) {
            this._buildProperty(name);
        }
    }

    _buildProperty(name) {
        Object.defineProperty(this, name, {
            get: function() {
                if (this._badges.hasOwnProperty(name)) {
                    return this._badges[name];
                }

                let ns = this._types[name],
                    operation = 'available_' + name + '_badges';

                if (!API.hasOwnProperty(ns) || !API[ns].hasOwnProperty(operation)) {
                    throw new BadgeError(`Badge for ${name} does not exists`);
                }

                let badges = this._badges[name] = {};

                API[ns][operation]({}, (response) => {
                    Object.assign(badges, response.obj);
                });

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
     * @param {Function} callback An optionnal callback function(badge)
     */
    add(obj, kind, callback) {
        let data = {payload: {kind: kind}},
            type = obj.constructor.__badges_type__,
            key = obj.constructor.__key__ || type,
            ns = this._types[type],
            operation = 'add_' + type + '_badge';

        data[key] = obj.id;

        API[ns][operation](data, function(response) {
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
     * @param {Function} callback An optionnal callback
     */
    remove(obj, kind, callback) {
        let data = {badge_kind: kind},
            type = obj.constructor.__badges_type__,
            key = obj.constructor.__key__ || type,
            ns = this._types[type],
            operation = 'delete_' + type + '_badge';

        data[key] = obj.id;

        API[ns][operation](data, function(response) {
            let badge = obj.badges.filter(function(o) {
                    return o.kind === kind;
                })[0];
            obj.badges.$remove(badge);
            if (callback) {
                callback();
            }
        });
    }
};

export var badges = new Badges(TYPES);

export default badges;
