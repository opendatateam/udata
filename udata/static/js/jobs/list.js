/**
 * Jobs listing
 */
define([
    'jquery',
    'auth',
    'i18n',
    'api',
    'notify',
    'widgets/modal',
    'hbs!templates/jobs/form',
    'form/common'
], function($, Auth, i18n, API, Notify, modal, jobFormTpl, forms) {
    'use strict';

    var schedulables,
        PERIODS = {
            minutes: i18n._('minutes'),
            hours: i18n._('hours'),
            days: i18n._('days'),
        };

    $('.add-btn').click(function() {
        var $modal = modal({
                title: i18n._('New job'),
                content: jobFormTpl({
                    schedulables: schedulables,
                    periods: PERIODS
                }),
                actions: [{
                    label: i18n._('Add'),
                    icon: 'fa-plus',
                    classes: 'btn-primary btn-submit'
                }]
            }),
            $form = $modal.find('form');


        $modal.on('shown.bs.modal', function() {
            $form.validate(forms.rules);
            $modal.find('.collapse').collapse();
            $modal.find('input[name=type]:radio').change(function() {
                $modal.find('.collapse').collapse('hide');
                $(this).closest('fieldset').find('.collapse').collapse('show');
            });

            $modal.find('.btn-submit').click(function() {
                var data = {
                    name: $form.find('#name-id').val(),
                    description: $form.find('#description-id').val(),
                    task: $form.find('#task-id').val(),
                };
                if ($form.find('input[name=type]').val() == 'crontab') {
                    data.crontab = {
                        minute: $form.find('#crontab-minute').val(),
                        hour: $form.find('#crontab-hour').val(),
                        day_of_week: $form.find('#crontab-day_of_week').val(),
                        day_of_month: $form.find('#crontab-day_of_month').val(),
                        month_of_year: $form.find('#crontab-month_of_year').val(),
                    };
                } else {
                    data.interval = {
                        every: $form.find('#interval-every').val(),
                        period: $form.find('#interval-period').val(),
                    };
                }
                API.post('/api/jobs/', data, function(job) {
                    console.log('Job created', job);
                });
            });
        });

        return false;
    });

    return {
        start: function() {
            API.get('/api/references/jobs', function(data) {
                schedulables = data;
            });
        }
    };

});
