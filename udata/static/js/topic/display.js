define(['jquery', 'dotdotdot'], function($) {
    "use strict";

    $(function() {
        // Handle ellipsis and more button
        $('.topic-excerpt').dotdotdot({
            callback: function( isTruncated, $content ) {
                var $more = $('.more');
                if (isTruncated) {
                    $more.removeClass('hide');
                } else {
                    $more.addClass('hide');
                }
            }
        });
    });

});
