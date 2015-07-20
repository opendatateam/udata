/**
 * Featured button
 */
define(['jquery', 'auth'], function($, Auth) {
    'use strict';

    // Handle featured button
    $('.btn.featured').click(function() {
        var $this = $(this);

        Auth.need_role('admin');

        if ($this.hasClass('active')) {
            $.ajax({
                url: $this.data('api-url'),
                type: 'DELETE',
                success: function(data) {
                    $this.removeClass('active');
                }
            })
        } else {
            $.post($this.data('api-url'), function(data) {
                $this.addClass('active');
            });
        }
    });

});
