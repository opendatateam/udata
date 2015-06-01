define(['jquery', 'bootstrap', 'dotdotdot'], function($) {

    $(function() {
        $('.ellipsis-dot').dotdotdot();

        $('.ellipsis-tooltip').dotdotdot({
            callback: function( isTruncated, orgContent ) {
                if (isTruncated) {
                    $(this).tooltip({
                        title: orgContent.text()
                    });
                }
            }
        });
    });

});
