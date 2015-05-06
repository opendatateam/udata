<template>
<box-container title="{{source.name}}" icon="cogs" boxclass="box-solid">
    <aside>
        <a class="text-muted pointer" v-on="click: toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <h3>
            {{source.name}}
            <small>{{source.backend}}</small>
        </h3>
        <div v-markdown="{{source.description}}"></div>
    </div>
    <form-vertical v-ref="form" v-if="toggled" fields="{{fields}}" object="{{source}}"></form-vertical>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-primary"
            v-on="click: save($event)" v-i18n="Save"></button>
    </box-footer>
</box-container>
</template>

<script>
'use strict';

module.exports = {
    name: 'source-details',
    paramAttributes: ['source'],
    data: function() {
        return {
            title: this._('Parameters'),
            toggled: false,
            fields: [{
                id: 'name',
                label: this._('Name')
            }, {
                id: 'backend',
                label: this._('Backend')
            }, {
                id: 'url',
                label: this._('URL')
            }, {
                id: 'description',
                label: this._('Description'),
            }, {
                id: 'active',
                label: this._('Active')
            }]
        };
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'form-vertical': require('components/form/vertical-form.vue')
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            var data = this.$.form.serialize();

            console.log(data);
            this.source.update(data);
            e.preventDefault();

            this.toggled = false;
        }
    }
};
</script>
