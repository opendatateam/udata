define(['hbs/handlebars'], function(Handlebars) {

    Handlebars.registerHelper('eachInMap', function(map, block) {
        var out = '';
        Object.keys(map).map(function(prop) {
            out += block.fn({key: prop, value: map[prop]});
        });
        return out;
    });

});
