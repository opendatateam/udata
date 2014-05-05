/**
 * Featured button
 */
define(['jquery'], function($) {
    'use strict';

    // Handle featured button
    $('.btn-star').click(function() {
        var $this = $(this);

        if ($this.hasClass('active')) {
            $.ajax({
                url: $this.data('api-url'),
                type: 'DELETE',
                success: function(data) {
                    $this
                        .removeClass('active')
                        .find('.glyphicon')
                            .removeClass('glyphicon-star')
                            .addClass('glyphicon-star-empty');
                }
            })
        } else {
            $.post($this.data('api-url'), function(data) {
                $this
                    .addClass('active')
                    .find('.glyphicon')
                            .removeClass('glyphicon-star-empty')
                            .addClass('glyphicon-star');
            });
        }
    });

});
