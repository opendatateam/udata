<style lang="less">
.org-profile-widget {
    .logo-button {
        border: 1px solid darken(white, 20%);
        float: left;
        margin: 0 10px 5px 0;
    }

    .box-body {
        h3 {
            margin-top: 0;
        }
    }

    .profile-body {
        min-height: 100px;
    }
}
</style>
<template>
<box-container title="{{ _('Profile') }}" icon="building"
    boxclass="box-solid org-profile-widget" footer="{{ toggled }}">
    <aside>
        <a class="text-muted pointer" @click="toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-show="!toggled">
        <h3>
            {{org.name}}
            <small v-if="org.acronym">{{org.acronym}}</small>
        </h3>
        <div class="profile-body">
            <image-button src="{{org.logo}}" size="100" class="logo-button"
                endpoint="{{endpoint}}">
            </image-button>
            <div :v-markdown="org.description"></div>
            <div v-if="org.badges | length" class="label-list">
                <strong>
                    <span class="fa fa-fw fa-bookmark"></span>
                    {{ _('Badges') }}:
                </strong>
                <span v-for="b in org.badges" class="label label-primary">{{badges[b.kind]}}</span>
            </div>
        </div>
    </div>
    <org-form v-ref:form v-show="toggled" organization="{{org}}"></org-form>
    <footer>
        <button type="submit" class="btn btn-primary" v-if="toggled"
            @click="save($event)" v-i18n="Save"></button>
    </footer>
</box-container>
</template>

<script>
'use strict';

var API = require('api');

module.exports = {
    name: 'org-profile',
    props: ['org'],
    data: function() {
        return {
            toggled: false,
            org: undefined,
            badges: require('models/badges').badges.organization
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'image-button': require('components/widgets/image-button.vue'),
        'org-form': require('components/organization/form.vue')
    },
    computed: {
        endpoint: function() {
            if (this.org.id) {
                var operation = API.organizations.operations.organization_logo;
                return operation.urlify({org: this.org.id});
            }
        }
    },
    events: {
        'image:saved': function() {
            this.org.fetch();
        }
    },
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            e.preventDefault();
            let form = this.$refs.form;
            if (form.validate()) {
                this.org.update(form.serialize(), (response) => {
                    this.org.on_fetched(response);
                    this.toggled = false;
                }, form.on_error);
            }
        },
    }
};
</script>
