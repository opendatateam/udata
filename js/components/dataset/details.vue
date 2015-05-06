<template>
<box-container title="{{title}}" icon="cubes" boxclass="box-solid">
    <aside>
        <a class="text-muted pointer" v-on="click: toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <h3>{{dataset.title}}</h3>
        <div v-markdown="{{dataset.description}}"></div>
    </div>
    <form-vertical v-ref="form" v-if="toggled" fields="{{fields}}" model="{{dataset}}"></form-vertical>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-primary"
            v-on="click: save($event)" v-i18n="Save"></button>
    </box-footer>
</box-container>
</template>
<script>
'use strict';

module.exports = {
    name: 'dataset-details',
    paramAttributes: ['dataset'],
    data: function() {
        return {
            title: this._('Details'),
            toggled: false,
            fields: [{
                id: 'title',
                label: this._('Name')
            }, {
                id: 'description',
                label: this._('Description'),
            }, {
                id: 'tags',
                label: this._('Tags'),
                widget: 'tag-completer'
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

            this.dataset.update(data);
            e.preventDefault();

            this.toggled = false;
        }
    }
};
</script>
