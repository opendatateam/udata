/**
 * Dataset display page JS module
 */
define([
    'jquery',
    'logger',
    'i18n',
    'auth',
    'api',
    'leaflet',
    'hbs!templates/dataset/resource-modal-body',
    'hbs!templates/dataset/add-reuse-modal-body',
    'form/common',
    'widgets/modal',
    'widgets/featured',
    'widgets/follow-btn',
    'widgets/issues-btn',
    'widgets/share-btn',
], function($, log, i18n, Auth, API, L, template, addReuseTpl, forms, modal) {
    'use strict';

    var user_reuses;

    function prepare_resources() {
        $('.resources-list').items('http://schema.org/DataDownload').each(function() {
            var $this = $(this);

            // Prevent default click on link
            $this.find('a[itemprop="url"]').click(function(e) {
                e.preventDefault();
            })

            // Ensure toolbar links does not interfere
            $this.find('.tools a').click(function(e) {
                e.stopPropagation();
            })

            // Display detailled informations in a modal
            $this.click(function() {
                modal({
                    title: $this.property('name').value(),
                    content: template($this.microdata()[0]),
                    actions: [{
                        label: i18n._('Download'),
                        url: $this.property('url').value(),
                        classes: 'btn-success'
                    }]
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

    function add_reuse() {
        var $this = $(this);
        if (user_reuses) {
            var url_pattern = $this.data('add-url'),
                $modal = modal({
                    title: i18n._('Add a reuse'),
                    content: addReuseTpl({
                        reuses: $.map(user_reuses, function(reuse) {
                            reuse.add_url = url_pattern.replace('{placeholder}', reuse.id);
                            return reuse;
                        }),
                        new_reuse_url: $this.attr('href'),
                        csrf_token: forms.csrftoken,
                        dataset: $('.dataset-container').attr('itemid')
                    })
                });
            $modal.on('shown.bs.modal', function() {
                forms.handle_postables($modal.find('a.reuse.postable'));
            });
            return false;
        }
    }

    function load_coverage_map() {
        var $el = $('#coverage-map'),
            attributions = '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> / <a href="http://open.mapquest.com/">MapQuest</a>',
            tilesUrl = 'http://otile{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png',
            map = L.map($el[0], {zoomControl: false}),
            layer = L.geoJson($el.data('geojson'));

        // Disable drag and zoom handlers.
        map.dragging.disable();
        map.touchZoom.disable();
        map.doubleClickZoom.disable();
        map.scrollWheelZoom.disable();

        // Disable tap handler, if present.
        if (map.tap) map.tap.disable();

        L.tileLayer(tilesUrl, {subdomains: '1234', attribution: attributions}).addTo(map);
        layer.addTo(map);
        map.fitBounds(layer.getBounds());
    }

    return {
        start: function() {
            log.debug('Dataset display page');
            prepare_resources();
            load_coverage_map();
            fetch_reuses();
            $('.reuse.add').click(add_reuse);
        }
    }
});
