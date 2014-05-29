/**
 * Follow button
 */
define(['jquery', 'auth', 'i18n'], function($, Auth, i18n) {
    'use strict';

    // Handle featured button
    $('.btn-follow').click(function() {
        var $this = $(this);

        Auth.need_user(i18n._('You need to be logged in to follow.'));

        if ($this.hasClass('active')) {
            $.ajax({
                url: $this.data('api-url'),
                type: 'DELETE',
                success: function(data) {
                    var $icon = $this.find('.glyphicon');

                    $icon
                        .removeClass('glyphicon-eye-open')
                        .addClass('glyphicon-eye-close');

                    $this.removeClass('active');

                    if ($this.content()) {
                        $this
                            .text(i18n._('Follow'))
                            .prepend($icon);
                    }

                }
            })
        } else {
            $.post($this.data('api-url'), function(data) {
                var $icon = $this.find('.glyphicon');

                $icon
                    .removeClass('glyphicon-eye-close')
                    .addClass('glyphicon-eye-open');

                $this.addClass('active');

                if ($this.content()) {
                    $this
                        .text(i18n._('Following'))
                        .prepend($icon);
                }
            });
        }
    });

});
