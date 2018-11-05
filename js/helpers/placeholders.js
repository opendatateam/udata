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
export const generic = reuse;

/**
 * Get an identicon (ie. deterministic avatar given an identifier)
 */
export function identicon(identifier, size) {
    return `${config.api_root}avatars/${identifier}/${size}`;
}

/**
 * Get an avatar url for a given user object.
 */
export function user_avatar(user, size) {
    if (!user) return;
    return user.avatar_thumbnail || user.avatar || identicon(user.id, size);
}

/**
 * Get a logo url for a given organization object.
 */
export function org_logo(org, size) {
    if (!org) return;
    return org.logo_thumbnail || org.logo || identicon(org.id, size);
}


export default {
    getFor,
    user_avatar,
    org_logo,
    organization,
    reuse,
    territory,
    generic,
    identicon,
};
