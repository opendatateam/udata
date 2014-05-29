/**
 * Featured button
 */
define(['jquery', 'auth', 'i18n'], function($, Auth, i18n) {
    'use strict';

    // Handle featured button
    $('.btn-star').click(function() {
        var $this = $(this);

        Auth.need_user(i18n._('You need to be logged in to star.'));

        if ($this.hasClass('active')) {
            $.ajax({
                url: $this.data('api-url'),
                type: 'DELETE',
                success: function(data) {
                    var $icon = $this.find('.glyphicon');

                    $icon
                        .removeClass('glyphicon-star')
                        .addClass('glyphicon-star-empty');

                    $this.removeClass('active');

                    if ($this.content()) {
                        $this
                            .text(i18n._('Star'))
                            .prepend($icon);
                    }
                }
            })
        } else {
            $.post($this.data('api-url'), function(data) {
                var $icon = $this.find('.glyphicon');

                $icon
                    .removeClass('glyphicon-star-empty')
                    .addClass('glyphicon-star');

                $this.addClass('active');

                if ($this.content()) {
                    $this
                        .text(i18n._('Starred'))
                        .prepend($icon);
                }
            });
        }
    });

});
