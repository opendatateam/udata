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
    'hbs!templates/jobs/item',
    'hbs!templates/jobs/delete-modal',
    'form/common'
], function($, Auth, i18n, API, Notify, modal, formTpl, itemTpl, deleteModalTpl, forms) {
    'use strict';

    var schedulables,
        $notifBar = $('.notifications-bar'),
        PERIODS = {
            minutes: i18n._('minutes'),
            hours: i18n._('hours'),
            days: i18n._('days'),
        };

    /**
     * Display a modal to create or edit a job
     */
    function display_modal(job) {
        var $modal = modal({
                title: i18n._('New job'),
                content: formTpl({
                    job: job,
                    schedulables: schedulables,
                    periods: PERIODS
                }),
                actions: [{
                    label: job ? i18n._('Save') : i18n._('Add'),
                    icon: job ? 'fa-save' : 'fa-plus',
                    classes: 'btn-primary btn-submit'
                }]
            }),
            $form = $modal.find('form');


        $modal.on('shown.bs.modal', function() {
            $form.validate(forms.rules);
            $modal.find('.fieldset-collapse').collapse({toggle: false});
            $modal.find('input[name=type]').change(function() {
                $modal.find('.fieldset-collapse').collapse('hide');
                $modal.find('input[name=type]:checked')
                    .closest('fieldset').find('.fieldset-collapse').collapse('show');
            });

            $modal.find('.btn-submit').click(function() {
                var promise,
                    data = {
                        name: $form.find('#name-id').val(),
                        description: $form.find('#description-id').val(),
                        task: $form.find('#task-id').val(),
                        enabled: $form.find('#enabled').val(),
                    };

                if ($form.find('input[name=type]:checked').val() == 'crontab') {
                    data.crontab = {
                        minute: $form.find('#crontab-minute').val(),
                        hour: $form.find('#crontab-hour').val(),
                        day_of_week: $form.find('#crontab-day_of_week').val(),
                        day_of_month: $form.find('#crontab-day_of_month').val(),
                        month_of_year: $form.find('#crontab-month_of_year').val()
                    };
                } else {
                    data.interval = {
                        every: $form.find('#interval-every').val(),
                        period: $form.find('#interval-period').val()
                    };
                }
                if (job) {
                    promise = API.put('/api/jobs/'+job.id, data, function(job) {
                        console.log('.jobs-table tr[data-id='+job.id+']',$('.job-table tr[data-id='+job.id+']'));
                        $('.jobs-table tr[data-id='+job.id+']').replaceWith(itemTpl(job));
                        Notify.success(i18n._('The job has been updated'), $notifBar);
                    });
                } else {
                    promise = API.post('/api/jobs/', data, function(job) {
                        $('.jobs-table tbody').append(itemTpl(job));
                        Notify.success(i18n._('The job has been created'), $notifBar);
                    });
                }
                promise.error(function(e) {
                    Notify.error(i18n._('Error trying to submit the job'), $notifBar);
                    console.error(e.responseJSON);
                }).always(function() {
                    toggleEmpty();
                    $modal.modal('hide');
                });
            });
        });
    }

    /**
     * Toggle the "Empty" row if necessary
     */
    function toggleEmpty() {
        if ($('tr.job').length > 0) {
            $('.empty').addClass('hide');
        } else {
            $('.empty').removeClass('hide');
        }
    }

    $('.add-btn').click(function() {
        display_modal();
        return false;
    });

    $('.jobs-table').on('click', '.job-edit', function() {
        var job_id = $(this).closest('tr.job').data('id');
        API.get('/api/jobs/'+job_id, function(job) {
            display_modal(job);
        });
        return false;
    });

    $('.jobs-table').on('click', '.job-delete', function() {
        var job_id = $(this).closest('tr.job').data('id'),
            $modal = modal({
                title: i18n._('Confirm deletion'),
                content: deleteModalTpl(),
                close_btn: i18n._('No'),
                actions: [{
                    label: i18n._('Yes'),
                    icon: 'fa-check',
                    classes: 'btn-primary'
                }]
            });

        $modal.find('.modal-footer .btn-primary').click(function() {
            API.delete('/api/jobs/'+job_id, function() {
                console.log($('.jobs-table tr.job[data-id='+job_id+']'), '.jobs-table tr.job[data-id='+job_id+']');
                $('.jobs-table tr.job[data-id='+job_id+']').remove();
                Notify.success(i18n._('Job has been deleted'), $notifBar);
            }).error(function(e) {
                Notify.error(i18n._('Error on deletion'), $notifBar);
                console.error(e.responseJSON);
            }).always(function() {
                toggleEmpty();
                $modal.modal('hide');
            });
            return false;
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
