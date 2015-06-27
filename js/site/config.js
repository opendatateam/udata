define(['jquery'], function($) {
    return {
        static_root: $('link[rel="static-root"]').attr('href')
    };
});
