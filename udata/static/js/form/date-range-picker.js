/**
 * Date range picker widget
 */
define(['jquery', 'moment', 'bootstrap-daterangepicker'], function($, moment) {
    'use strict';

    moment.lang($('html').attr('lang')); // Set it globally in a module
    $('.dtpicker').each(function() {
        var $this = $(this),
            $widget = $('<input type="text" class="form-control" />'),
            $clearBtn = $('<button type="button" class="btn btn-warning" />'),
            startDate = $this.data('start-date'),
            endDate = $this.data('end-date'),
            display = function(start, end) {
                if (start && end) {
                    $widget.val(start.format('LL') + ' - ' + end.format('LL'));
                    $this.val(start.format('YYYY-MM-DD') + ' - ' + end.format('YYYY-MM-DD'));
                } else {
                    $widget.val('');
                    $this.val('');
                }
            };

        startDate = startDate ? moment(startDate) : undefined;
        endDate = endDate ? moment(endDate) : undefined;

        display(startDate, endDate);

        $this.removeClass('form-control').before($widget);

        $widget
            .wrap('<div class="input-group">')
            .before('<span class="input-group-addon"><span class="glyphicon glyphicon-calendar"/></span>')
            .after($clearBtn)
            .daterangepicker({
                showDropdowns: true,
                startDate: startDate,
                endDate: endDate
            }, display);

        $clearBtn
            .wrap('<span class="input-group-btn">')
            .append('<span class="glyphicon glyphicon-remove"></span>')
            .click(display);
    });

});
