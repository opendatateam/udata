<template>
<box-container title="{{title}}" icon="cubes" boxclass="box-solid">
    <aside>
        <a class="text-muted pointer" @click="toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-show="!toggled">
        <h3>{{dataset.title}}</h3>
        <div v-markdown="{{dataset.description}}"></div>
        <div v-if="dataset.tags | length" class="label-list">
            <strong>
                <span class="fa fa-fw fa-tags"></span>
                {{ _('Tags') }}:
            </strong>
            <span v-repeat="dataset.tags" class="label label-default">{{$value}}</span>
        </div>
        <div v-if="dataset.badges | length" class="label-list">
            <strong>
                <span class="fa fa-fw fa-bookmark"></span>
                {{ _('Badges') }}:
            </strong>
            <span v-repeat="dataset.badges" class="label label-primary">{{badges[kind]}}</span>
        </div>
    </div>
    <dataset-form v-ref:form v-show="toggled" dataset="{{dataset}}"></dataset-form>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-primary"
            @click="save($event)" v-i18n="Save"></button>
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
            toggled: false,
            badges: require('models/badges').badges.dataset
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
            e.preventDefault();
            let form = this.$refs.form;
            if (form.validate()) {
                this.dataset.update(form.serialize(), (response) => {
                    this.dataset.on_fetched(response);
                    this.toggled = false;
                }, form.on_error);
            }
        }
    }
};
</script>
