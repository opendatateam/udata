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
    boxclass="box-solid org-profile-widget">
    <aside>
        <a class="text-muted pointer" v-on="click: toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <h3>
            {{org.name}}
            <small v-if="org.acronym">{{org.acronym}}</small>
        </h3>
        <div class="profile-body">
            <image-button src="{{org.logo}}" size="100" class="logo-button"
                endpoint="{{endpoint}}">
            </image-button>
            <div v-markdown="{{org.description}}"></div>
        </div>
    </div>
    <create-form v-ref="form" v-if="toggled" organization="{{org}}"></create-form>
    <box-footer v-if="toggled">
        <button type="submit" class="btn btn-primary"
            v-on="click: save($event)" v-i18n="Save"></button>
    </box-footer>
</box-container>
</template>

<script>
'use strict';

var API = require('api');

module.exports = {
    name: 'org-profile',
    paramAttributes: ['org'],
    data: function() {
        return {
            toggled: false,
            org: undefined
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'image-button': require('components/widgets/image-button.vue'),
        'create-form': require('components/organization/create-form.vue')
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
