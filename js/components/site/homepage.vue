<template>
<div>
    <div class="nav-tabs-custom" v-show="!toggled">
        <ul class="nav nav-tabs">
            <li class="header">
                <i class="fa fa-home"></i>
                {{title}}
            </li>
            <li v-class="active: tab == 'datasets'">
                <a class="pointer" v-i18n="Datasets" v-on="click: tab = 'datasets'"></a>
            </li>
            <li v-class="active: tab == 'reuses'">
                <a class="pointer" v-i18n="Reuses" v-on="click: tab = 'reuses'"></a>
            </li>
            <li class="pull-right">
                <a class="text-muted pointer" v-on="click: toggle">
                    <i class="fa fa-gear"></i>
                </a>
            </li>
        </ul>
        <div class="tab-content">
            <div class="tab-pane" v-class="active: tab == 'datasets'">
                <div class="row">
                    <dataset-card class="col-md-6"
                        v-repeat="datasetid:settings.datasets"
                    ></dataset-card>
                </div>
            </div>
            <div class="tab-pane"  v-class="active: tab == 'reuses'">
                <div class="row">
                    <reuse-card class="col-md-6"
                        v-repeat="reuseid:settings.reuses"
                    ></reuse-card>
                </div>
            </div>
        </div>
    </div>
    <!-- Edition mode -->
    <box-container v-show="toggled" icon="home" title="{{title}}" boxclass="box-primary">
        <form-vertical v-ref="datasetform" v-show="tab == 'datasets'"
            fields="{{datasets_fields}}" model="{{settings}}"
        ></form-vertical>
        <form-vertical v-ref="reuseform" v-show="tab == 'reuses'"
            fields="{{reuses_fields}}" model="{{settings}}"
        ></form-vertical>
        <box-footer>
            <div class="btn-toolbar">
                <div class="btn-group">
                    <button type="submit" class="btn btn-success btn-flat"
                        v-on="click: save($event)" v-i18n="Save">
                        {{ _('Save') }}
                    </button>
                </div>
                <div class="btn-group">
                    <button type="button" class="btn btn-warning btn-flat pull-right"
                        v-on="click: toggled = false">
                        {{ _('Cancel') }}
                    </button>
                </div>
            </div>
        </box-footer>
    </box-container>
</div>
</template>

<script>
'use strict';

module.exports = {
    name: 'homepage-widget',
    replace: true,
    data: function() {
        return {
            title: this._('Homepage'),
            tab: 'datasets',
            footer: true,
            datasets_fields: [{
                id: 'datasets',
                label: this._('Datasets'),
                widget: 'dataset-completer'
            }],
            reuses_fields: [{
                id: 'reuses',
                label: this._('Reuses'),
                widget: 'reuse-completer'
            }],
            toggled: false
        };
    },
    computed: {
        settings: function() {
            if (!this.site || !this.site.settings || !this.site.settings.home) {
                return {};
            }
            return this.site.settings.home || {};
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'dataset-card': require('components/dataset/card.vue'),
        'reuse-card': require('components/reuse/card.vue'),
        'form-vertical': require('components/form/vertical-form.vue')
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            if (this.$.form.$.form.validate()) {
                var data = this.$.form.$.form.serialize();

                this.org.update(data);
                e.preventDefault();

                this.toggled = false;
            }
        }
    }
};
</script>
