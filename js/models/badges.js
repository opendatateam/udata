import API from 'api';
import BaseError from 'models/error';

export class BadgeError extends BaseError {};


/**
 * A simple cache for badges
 */
export class Badges {

    constructor() {
        this._badges = {};

        // Parse all models with badges
        for (let model of Object.keys(API.definitions)) {
            this._checkDefinition(API.definitions[model], model);
        }
    }

    _checkDefinition(definition, model) {
        if (!definition) return;
        if ('properties' in definition && 'badges' in definition.properties) {
            this._buildProperty(model.toLowerCase());
            return;
        }
        if ('allOf' in definition) {
            for (let nested of definition.allOf) {
                if ('$ref' in nested) {
                    let resolved = API.resolve(nested.$ref);
                    this._checkDefinition(resolved, model);
                } else {
                    this._checkDefinition(nested, model)
                }
            }
        }
    }

    _buildProperty(name) {
        Object.defineProperty(this, name, {
            get: function() {
                if (this._badges.hasOwnProperty(name)) {
                    return this._badges[name];
                }

                var namespace = name + 's',
                    operation = 'available_' + name + '_badges';

                if (!API.hasOwnProperty(namespace) || !API[namespace].hasOwnProperty(operation)) {
                    throw new BadgeError(`Badge for ${name} does not exists`);
                }

                let badges = this._badges[name] = {};

                API[namespace][operation]({}, (response) => {
                    Object.assign(badges, response.obj);
                });

                return badges;
            }
        });
    }
};

export var badges = new Badges();

export default badges;
