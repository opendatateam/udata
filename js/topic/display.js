import $ from 'jquery';
import 'jQuery.dotdotdot';

$(function() {
    // Handle ellipsis and more button
    $('.topic-excerpt').dotdotdot({
        callback: function(isTruncated) {
            const $more = $('.more');
            if (isTruncated) {
                $more.removeClass('hide');
            } else {
                $more.addClass('hide');
            }
        }
    });
});
