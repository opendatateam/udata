define([
    'jquery',
    'logger',
    'class',
    'hbs!templates/map/coverage-popup',
    'leaflet',
    'spin',
    'leaflet.spin'
], function($, log, Class, popupTpl, L, Spinner) {
    'use strict';

    var DEFAULTS = {
            levels_url: '/api/references/spatial/levels/',
            coverage_url: '/api/spatial/coverage/{level}/',
            style: {
                clickable: true,
                weight: 0.5,
                opacity: 0.5,
                fillOpacity: 0.3
            },
            hover_style: {
                fillOpacity: 0.8
            },
            attributions: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> / <a href="http://open.mapquest.com/">MapQuest</a>',
            tilesUrl: 'http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png'
        };


    if (!window.Spinner) { // Fix for leaflet.spin
        window.Spinner = Spinner;
    }

    function sort_levels(a, b) {
        return a.position - b.position;
    }

    function random_color() {
        var letters = '0123456789ABCDEF'.split(''),
            color = '#';

        for (var i = 0; i < 6; i++) {
            color += letters[Math.round(Math.random() * 15)];
        }
        return color;
    }

    var CoverageMap = Class.extend({
        init: function(el, opts) {
            this.$el = $(el);
            this.opts = $.extend(true, {}, DEFAULTS, opts);
        },

        load: function() {
            log.debug('Loading coverage map');
            this.map = L.map(this.$el[0]);
            this.map.spin(true);
            $.get(this.opts.levels_url, $.proxy(this.on_levels_loaded, this));
        },

        on_levels_loaded: function(data) {
            var layers = {};

            this.levels = $.map(data.sort(sort_levels), $.proxy(function(level, idx) {
                var layer = L.geoJson(null, {
                    style: this.opts.style,
                    onEachFeature: $.proxy(this.on_each_feature, this)
                });
                level.data_url = this.layer_url(level);
                level.layer = layer;

                layer.level = level;
                layers[level.label] = layer;
                return level;
            }, this));

            L.tileLayer(this.opts.tilesUrl, {
                subdomains: '1234',
                attribution: this.opts.attributions
            }).addTo(this.map);

            L.control.layers(layers, null, {collapsed: false}).addTo(this.map);
            this.map.on('baselayerchange', $.proxy(function(ev) {
                this.switch_level(ev.layer.level);
            }, this));

            this.switch_level(this.levels[0]);
        },

        /**
         * Display a given level
         */
        switch_level: function(level) {
            if (typeof level == 'string' || level instanceof String) {
                level = $.grep(this.levels, function(current_level) {
                    return current_level.id == level;
                })[0];
            }

            if (level.layer == this.layer) {
                // already set
                return;
            }

            this.map.spin(true);
            // if (!this.map._spinner) {
            // }

            this.children_level = $.grep(this.levels, function(l) {
                return l.parent == level.id;
            });

            if (this.layer && this.map.hasLayer(this.layer)) {
                this.map.removeLayer(this.layer);
            }
            this.layer = level.layer;
            if (!this.map.hasLayer(level.layer)) {
                level.layer.addTo(this.map);
            }

            if (!level.layer.loaded) {
                $.get(level.data_url, $.proxy(function(data) {
                    level.layer.loaded = true;
                    this.layer.addData(data);
                    this.data_loaded();
                }, this));
            } else {
                this.data_loaded();
            }
        },

        layer_url: function(level) {
            return this.opts.coverage_url.replace('{level}', level.id);
        },

        /**
         * End the loading state and center the map on the chosen bounds
         */
        data_loaded: function() {
            this.map.fitBounds(this.bounds || this.layer.getBounds());
            while(this.map._spinner) {
                this.map.spin(false);
            }
            this.bounds = null;
        },

        /**
         * Apply style to each feature:
         */
        on_each_feature: function(feature, layer) {
            var cls = this,
                base_color = random_color(),
                $popup = $(popupTpl({feature:feature, children: this.children_level}));

            layer.setStyle($.extend({}, cls.opts.style, {
                color: base_color,
                fillColor: base_color
            }));

            $popup.find('.drill-down').click(layer, $.proxy(this.on_feature_popup_click, this));

            layer.bindPopup($popup[0]);
            layer.on('mouseover', function () {
                layer.setStyle(cls.opts.hover_style);
            });
            layer.on('mouseout', function () {
                layer.setStyle(cls.opts.style);
            });
        },

        on_feature_popup_click: function(ev, feature) {
            this.bounds = ev.data.getBounds();
            this.switch_level($(ev.target).data('level'));
            return false;
        }
    });

    return CoverageMap;
});


