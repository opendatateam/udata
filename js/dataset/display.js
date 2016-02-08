/**
 * Dataset display page JS module
 */
import $ from 'jquery';
import config from 'config';
import log from 'logger';
import i18n from 'i18n';
import Auth from 'auth';
import API from 'api.light';
import utils from 'utils';
import L from 'leaflet';
import pubsub from 'pubsub';
import template from 'templates/dataset/resource-modal-body.hbs';
import extrasTpl from 'templates/dataset/extras-modal-body.hbs';
import addReuseTpl from 'templates/dataset/add-reuse-modal-body.hbs';
import modal from 'widgets/modal';
import 'widgets/follow-btn';
import 'widgets/issues-btn';
import 'widgets/discussions-btn';
import 'widgets/share-btn';
import 'widgets/integrate-btn';

// Current page dataset microdata
const $Dataset = $('body').items('http://schema.org/Dataset').eq(0);

let user_reuses;

function addTooltip($element, content) {
    $element.attr('rel', 'tooltip');
    $element.attr('data-placement', 'top');
    $element.attr('data-original-title', content);
    $element.tooltip('show');
}

function prepare_resources() {
    $('.resources-list').items('http://schema.org/DataDownload').each(function() {
        const $this = $(this);

        // Prevent default click on link
        $this.find('a[itemprop="url"]').click(function(e) {
            e.preventDefault();
        });

        // Ensure toolbar links does not interfere
        $this.find('.tools a').click(function(e) {
            e.stopPropagation();
        });

        // Check asynchronuously the status of displayed resources
        if (config.check_urls) {
            $this.find('.format-label').each(function() {
                const $self = $(this);
                const url = $self.parent().property('url').first().attr('href');
                const group = $Dataset.property('alternateName').value(); // This is the slug.

                if (!url.startsWith(window.location.origin)
                // TODO: temporary fix before we move all statics on the same server
                    && !url.match(/:\/\/(.[^/]+)/)[1].endsWith('data.gouv.fr')) {
                        if (url.startsWith('ftp')) {
                            $self.addClass('format-label-warning');
                            addTooltip($self, i18n._('The server may be hard to reach (FTP).'));
                        } else {
                            $.get($this.data('checkurl'), {'url': url, 'group': group}
                            ).done((data) => {
                                if (data.status === '200') {
                                    $self.addClass('format-label-success');
                                } else if (data.status === '404') {
                                    $self.addClass('format-label-warning');
                                    addTooltip($self, i18n._('The resource cannot be found.'));
                                }
                            }).fail((jqXHR) => {
                                // The API check returns a 503 if the croquemort server itself is unreachable
                                if (jqXHR.status !== 503) {
                                    $self.addClass('format-label-danger');
                                    addTooltip($self, i18n._('The server cannot be found.'));
                                }
                            });
                    }
                }
            });
        }

        // Display detailled informations in a modal
        $this.click(function() {
            const $modal = modal({
                title: $this.property('name').value(),
                content: template($this.microdata()[0]),
                actions: [{
                    label: i18n._('Download'),
                    url: $this.property('url').value(),
                    classes: 'btn-success resource-click'
                }]
            });
            // Click on a download link
            $modal.find('.resource-click').click(function() {
                let eventName = '';
                if (startsWith(this.href, window.location.origin)) {
                    eventName = 'RESOURCE_DOWNLOAD';
                } else {
                    eventName = 'RESOURCE_REDIRECT';
                }
                pubsub.publish(eventName);
            });
        });
    });

    // Hide expander on click
    $('.expander').click(function() {
        $(this).animate({height: 0, opacity: 0}, function() {
            $(this).remove();
        });
    });
}

function fetch_reuses() {
    if (Auth.user) {
        API.get('/me/reuses/', function(data) {
            user_reuses = data;
        });
    }
}

function loadJson(map, layer, data) {
    layer.addData(data);
    layer.addTo(map);
    map.fitBounds(layer.getBounds());
}

function load_coverage_map() {
    const $el = $('#coverage-map');
    const ATTRIBUTIONS = [
            '&copy;',
            '<a href="http://openstreetmap.org">OpenStreetMap</a>',
            '/',
            '<a href="http://open.mapquest.com/">MapQuest</a>'
        ].join(' ');
    const TILES_PREFIX = location.protocol === 'https:' ? '//otile{s}-s' : '//otile{s}';
    const TILES_URL = TILES_PREFIX + '.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png';
    const TILES_CONFIG = {subdomains: '1234', attribution: ATTRIBUTIONS};
    let map;
    let layer;

    if (!$el.length) {
        return;
    }

    map = L.map($el[0], {zoomControl: false});

    // Disable drag and zoom handlers.
    map.dragging.disable();
    map.touchZoom.disable();
    map.doubleClickZoom.disable();
    map.scrollWheelZoom.disable();

    // Disable tap handler, if present.
    if (map.tap) map.tap.disable();

    L.tileLayer(TILES_URL, TILES_CONFIG).addTo(map);

    layer = L.geoJson(null, {
        onEachFeature: function(feature, layer) {
            layer.bindPopup(feature.properties.name);
            layer.on('mouseover', function() {
                layer.openPopup();
            });
            layer.on('mouseout', function() {
                layer.closePopup();
            });
        }
    });

    if ($el.data('geojson')) {
        loadJson(map, layer, $el.data('geojson'));
    } else if ($el.data('zones')) {
        $.get($el.data('zones'), function(data) {
            loadJson(map, layer, data);
        });
    }
}

function display_extras() {
    const data = $Dataset.microdata()[0];

    data.id = $Dataset.attr('itemid');
    if (utils.isString(data.keywords)) {
        data.keywords = [data.keywords];
    }
    modal({
        title: i18n._('Details'),
        content: extrasTpl(data)
    });
}

function add_reuse() {
    const $this = $(this);
    if (user_reuses) {
        const $modal = modal({
            title: i18n._('Add a reuse'),
            content: addReuseTpl({
                reuses: user_reuses,
                new_reuse_url: $this.attr('href'),
                dataset: $('.dataset-container').attr('itemid')
            })
        });
        $modal.on('shown.bs.modal', function() {
            $modal.find('a.reuse.clickable').click(function() {
                const reuse_id = $(this).data('id');
                const dataset_id = $Dataset.attr('itemid');
                const api_url = '/reuses/' + reuse_id + '/datasets/';
                const data = {id: dataset_id, class: 'Dataset'};
                API.post(api_url, data, function(data) {
                    window.location = config.admin_root + 'reuse/' + reuse_id;
                });
                return false;
            });
        });
        return false;
    }
}

$(function() {
    log.debug('Dataset display page');
    $('.reuse.add').click(add_reuse);
    $('.btn-extras').click(display_extras);
    load_coverage_map();
    prepare_resources();
    fetch_reuses();
});
