/**
 * Follow button
 */
define(['jquery'], function($) {
    'use strict';

    // Handle featured button
    $('.btn-follow').click(function() {
        var $this = $(this);

        if ($this.hasClass('active')) {
            $.ajax({
                url: $this.data('api-url'),
                type: 'DELETE',
                success: function(data) {
                    $this
                        .removeClass('active')
                        .find('.glyphicon')
                            .removeClass('glyphicon-eye-open')
                            .addClass('glyphicon-eye-close');
                }
            })
        } else {
            $.post($this.data('api-url'), function(data) {
                $this
                    .addClass('active')
                    .find('.glyphicon')
                            .removeClass('glyphicon-eye-close')
                            .addClass('glyphicon-eye-open');
            });
        }
    });

});
