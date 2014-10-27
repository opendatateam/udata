/**
 * Display a file size in human-readable way
 */
define(['hbs/handlebars'], function(Handlebars) {

    function bytesToSize(bytes) {
        var sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        if (!bytes) return 'n/a';
        var i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        if (i == 0) return bytes + ' ' + sizes[i];
        return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i];
    };

    Handlebars.registerHelper('size', function(value, options) {
        return bytesToSize(value);
    });
});
