define(['backbone', 'hbs/handlebars', 'marked'], function(Backbone, Handlebars, marked) {
    // From http://stackoverflow.com/a/19431552
    // Compatibility override - Backbone 1.1 got rid of the 'options' binding
    // automatically to views in the constructor - we need to keep that.
    Backbone.View = (function(View) {
       return View.extend({
            constructor: function(options) {
                this.options = options || {};
                View.apply(this, arguments);
            }
        });
    })(Backbone.View);

    window.Handlebars = Handlebars;
    window.marked = marked;

    return Backbone;
});
