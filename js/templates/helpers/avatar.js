define([
    'handlebars',
    'utils/placeholder',
    'templates/avatar.hbs'
], function(Handlebars, placeholder, tpl) {

    return function(object, size, options) {
        var avatar_url,
            type = options.hash['type'] || 'user';

        if (!object) {
            return;
        } else if ('avatar_url' in object) {
            avatar_url = object.avatar_url;
        } else if ('image_url' in object) {
            avatar_url = object.image_url;
        }

        return new Handlebars.SafeString(tpl({
            href: options.hash['url'] || undefined,
            avatar_url: avatar_url || placeholder.default(type),
            avatar_size: size || 32
        }));

    };

});
