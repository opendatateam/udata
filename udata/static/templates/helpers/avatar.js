define([
    'hbs/handlebars',
    'utils/placeholder',
    'hbs!templates/avatar'
], function(Handlebars, placeholder, tpl) {

    Handlebars.registerHelper('avatar', function(object, size, options) {
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
            avatar_url: avatar_url || placeholder(type),
            size: size || 32
        }));

    });

});
