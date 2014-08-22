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

    var schedulables;

    $('.add-btn').click(function() {
        var $modal = modal({
                title: i18n._('New job'),
                content: jobFormTpl({
                    csrf_token: forms.csrktoken,
                    schedulables: schedulables
                }),
                actions: [{
                    label: i18n._('Add'),
                    icon: 'fa-plus',
                    classes: 'btn-primary btn-submit'
                }]
            }),
            $form = $modal.find('form');

        $form.validate(forms.rules);

        $modal.find('.btn-submit').click(function() {
            $modal.find('form').submit();
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
