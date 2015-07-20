/**
 * Temporal coverage search facet
 */
define([
    'logger',
    'jquery',
    'moment',
    'i18n',
    'bootstrap-datepicker/dist/js/bootstrap-datepicker.js'
], function(log, $, moment, i18n) {
    'use strict';

    // Use the same localization than moment
    $.fn.datepicker.dates[i18n.lang] = {
        days: moment.weekdays(),
        daysShort: moment.weekdaysShort(),
        daysMin: moment.weekdaysMin(),
        months: moment.months(),
        monthsShort: moment.monthsShort(),
        today: i18n._('Today'),
        clear: i18n._('Clear')
    };

    $('.temporal-coverage').each(function() {
        var $panel = $(this),
            $picker = $panel.find('.facet-datepicker'),
            $current = null;

        $panel.find('.input-daterange input').each(function() {
            var $this = $(this);

            // Set initial value
            $this.val(moment($this.data('isodate')).format('L'));

            // Handle picker displya on input or focus
            $this.on('click focus', function() {
                var dt = moment($this.data('isodate'));

                $current = $this;
                $picker.datepicker('update', dt.toDate())
                $panel.find('.hide').removeClass('hide');
            })
            // Handle user input
            .on('input', function() {
                var dt = moment($this.val(), 'L', true);
                if (dt.isValid()) {
                    $this.data('isodate', dt.format('YYYY-MM-DD'));
                    if ($this == $current && !$picker.hasClass('hide')) {
                        $picker.datepicker('update', dt.toDate());
                        $picker.addClass('hide');
                    }
                }
            });

        });

        $picker
            .datepicker({
                format: "yyyy-mm-dd",
                language: i18n.lang,
                weekStart: moment.localeData()._week.dow
            })
            .on('changeDate', function(e) {
                if ($current) {
                    var dt = moment(e.date);
                    $current.data('isodate', dt.format('YYYY-MM-DD'));
                    $current.val(dt.format('L'));
                    $picker.addClass('hide');
                }
            });

        // Submit search on "Apply click"
        $panel.find('.btn-apply').click(function() {
            var filter = [
                $panel.find('[name=start]').data('isodate'),
                $panel.find('[name=end]').data('isodate')
            ].join('-')
            window.location = $panel.data('url-pattern').replace('__r__', filter);
        });

    });

});
