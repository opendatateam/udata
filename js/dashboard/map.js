import config from 'config';
import $ from 'jquery';
import API from 'api.light';
import log from 'logger';
import popupTpl from 'templates/map/coverage-popup.hbs';
import L from 'leaflet';
import Spinner from 'spin.js';
import 'vendor/leaflet.spin';

const DEFAULTS = {
        style: {
            clickable: true,
            weight: 0.5,
            opacity: 0.5,
            fillOpacity: 0.3
        },
        hover_style: {
            fillOpacity: 0.8
        }
    },
    LEVELS_URL = '/spatial/levels',
    COVERAGE_URL = '/spatial/coverage/{level}';


if (!window.Spinner) { // Fix for leaflet.spin
    window.Spinner = Spinner;
}

function sort_levels(a, b) {
    return a.position - b.position;
}

function random_color() {
    let letters = '0123456789ABCDEF'.split(''),
        color = '#';

    for (let i = 0; i < 6; i++) {
        color += letters[Math.round(Math.random() * 15)];
    }
    return color;
}

export default class CoverageMap {
    constructor(el, opts) {
        this.$el = $(el);
        this.opts = $.extend(true, {}, DEFAULTS, opts);
    }

    load() {
        log.debug('Loading coverage map');
        this.map = L.map(this.$el[0]);
        this.map.spin(true);
        API.get(LEVELS_URL, this.on_levels_loaded.bind(this));
    }

    on_levels_loaded(data) {
        let layers = {};

        this.levels = data.sort(sort_levels).map((level, idx) => {
            let layer = L.geoJson(null, {
                style: this.opts.style,
                onEachFeature: this.on_each_feature.bind(this)
            });
            level.data_url = this.layer_url(level);
            level.layer = layer;

            layer.level = level;
            layers[level.name] = layer;
            return level;
        });

        L.tileLayer(config.tiles_url, config.tiles_config).addTo(this.map);

        L.control.layers(layers, null, {collapsed: false}).addTo(this.map);
        this.map.on('baselayerchange', (ev) => {
            this.switch_level(ev.layer.level);
        });

        this.switch_level(this.levels[0]);
    }

    /**
     * Display a given level
     */
    switch_level(level) {
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
            API.get(level.data_url, $.proxy(function(data) {
                level.layer.loaded = true;
                this.layer.addData(data);
                this.data_loaded();
            }, this));
        } else {
            this.data_loaded();
        }
    }

    layer_url(level) {
        return COVERAGE_URL.replace('{level}', level.id);
    }

    /**
     * End the loading state and center the map on the chosen bounds
     */
    data_loaded() {
        this.map.fitBounds(this.bounds || this.layer.getBounds());
        while(this.map._spinner) {
            this.map.spin(false);
        }
        this.bounds = null;
    }

    /**
     * Apply style to each feature:
     */
    on_each_feature(feature, layer) {
        let cls = this,
            base_color = random_color(),
            $popup = $(popupTpl({feature:feature, children: this.children_level}));

        layer.setStyle($.extend({}, cls.opts.style, {
            color: base_color,
            fillColor: base_color
        }));

        $popup.find('.drill-down').click(layer, this.on_feature_popup_click.bind(this));

        layer.bindPopup($popup[0]);
        layer.on('mouseover', function () {
            layer.setStyle(cls.opts.hover_style);
        });
        layer.on('mouseout', function () {
            layer.setStyle(cls.opts.style);
        });
    }

    on_feature_popup_click(ev, feature) {
        this.bounds = ev.data.getBounds();
        this.switch_level($(ev.target).data('level'));
        return false;
    }
};
