define(['jquery', 'd3', 'class'], function($, d3, Class) {

    var BaseChart = Class.extend({
        init: function(el) {
            this.$el = $(el);
            this.el = this.$el[0];
            this.$chart = this.$el.find('.chart');
            this._build();
        },

        _build: function() {
            this.$infobox = $('<div class="infobox"/>');

            this.$infobox.append($('<span class="value" />'));
            this.$infobox.append($('<span class="diff" />'));
            this.$infobox.append($('<span class="label" />'));

            this.$chart.empty().append(this.$infobox);

            this.d3 = d3.select(this.$chart[0]);
            this.svg = this.d3.append("svg:svg");
        },

        bbox: function() {
            return this.$chart[0].getBoundingClientRect();
        },

        _setInfobox: function(value, diff, label, css) {
            this.$infobox.find('span.value').html(value);
            this.$infobox.find('span.diff').html(diff);
            this.$infobox.find('span.label').html(label);
            this.$infobox.css(css);
            this.$infobox.addClass('selected');
        }
    });

    return BaseChart;

});
