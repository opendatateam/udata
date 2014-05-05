define(['jquery', 'bootstrap', 'dotdotdot'], function($) {


	$(function() {
	    // Set simple ellipsis
	    $('.ellipsis-dot').dotdotdot({
	        watch: true
	    });

	    $('.ellipsis-tooltip').dotdotdot({
	        watch: true,
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
