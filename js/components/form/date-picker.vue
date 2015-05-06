<style lang="less">

</style>

<template>
<div class="input-group">
    <span class="input-group-addon"><span class="fa fa-calendar"/></span></span>
    <input type="text" class="form-control" />
</div>
</template>

<script>
'use strict';
var $ = require('jquery'),
    moment = require('moment');

require('bootstrap-daterangepicker');

module.exports = {
    data: function() {
        return {};
    },
    ready: function() {
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
                endDate: endDate,
                format: 'L',
                locale: {
                    applyLabel: i18n._('OK'),
                    cancelLabel: i18n._('Cancel'),
                    fromLabel: i18n._('From'),
                    toLabel: i18n._('To'),
                    customRangeLabel: i18n._('Custom Range'),
                    firstDay: moment.localeData()._week.dow
                }
            }, display);

        $clearBtn
            .wrap('<span class="input-group-btn">')
            .append('<span class="glyphicon glyphicon-remove"></span>')
            .click(display);
    }
};
</script>
