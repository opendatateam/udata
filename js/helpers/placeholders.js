import config from 'config';

/**
 * Resolve placeholder for a given type
 */
export function getFor(type) {
	return `${config.theme_static}img/placeholders/${type}.png`;
}

/**
 * Organization placeholder
 */
export const organization = getFor('organization');

/**
 * User placeholder
 */
export const user = getFor('user');

/**
 * Reuse placeholder
 */
export const reuse = getFor('reuse');

/**
 * Territory placeholder
 */
export const territory = `${config.theme_static}img/placeholder_territory_medium.png`;

/**
 * Generic placeholder
 */
export const generic = user;


export default {
    getFor,
    user,
    organization,
    reuse,
    territory,
    generic,
};
