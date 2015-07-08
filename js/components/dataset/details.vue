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
        <div v-if="dataset.tags" class="label-list">
            <strong>
                <span class="fa fa-fw fa-tags"></span>
                {{ _('Tags') }}:
            </strong>
            <span v-repeat="dataset.tags" class="label label-default">{{$value}}</span>
        </div>
        <div v-if="dataset.badges" class="label-list">
            <strong>
                <span class="fa fa-fw fa-bookmark"></span>
                {{ _('Badges') }}:
            </strong>
            <span v-repeat="dataset.badges" class="label label-primary">{{kind}}</span>
        </div>
    </div>
    <dataset-form v-ref="form" v-if="toggled" dataset="{{dataset}}"></dataset-form>
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
    props: ['dataset'],
    data: function() {
        return {
            title: this._('Details'),
            toggled: false
        };
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'dataset-form': require('components/dataset/form.vue')
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            if (this.$.form.validate()) {
                var data = this.$.form.serialize();

                this.dataset.update(data);
                e.preventDefault();

                this.toggled = false;
            }
        }
    }
};
</script>
