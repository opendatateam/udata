<style lang="less">
.user-profile-widget {
    .avatar-button {
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
<box-container footer="{{ toggled }}" title="{{title}}" icon="user" boxclass="user-profile-widget">
    <aside>
        <a class="text-muted pointer" v-on="click: toggle">
            <i class="fa fa-gear"></i>
        </a>
    </aside>
    <div v-if="!toggled">
        <h3>
            {{user.fullname}}
        </h3>
        <div class="profile-body">
            <image-button src="{{user.avatar}}" size="100" class="avatar-button"
                endpoint="{{endpoint}}">
            </image-button>
            <div v-markdown="{{user.about}}"></div>
        </div>
    </div>
    <user-form v-ref="form" v-if="toggled" user="{{user}}"></user-form>
    <footer>
        <button type="submit" class="btn btn-primary"
            v-on="click: save($event)" v-i18n="Save"></button>
    </footer>
</box-container>
</template>
<script>
'use strict';

var API = require('api');

module.exports = {
    name: 'user-profile',
    data: function() {
        return {
            title: this._('Profile'),
            toggled: false
        };
    },
    computed: {
        endpoint: function() {
            var operation = API.me.operations.my_avatar;
            return operation.urlify({});
        }
    },
    components: {
        'box-container': require('components/containers/box.vue'),
        'image-button': require('components/widgets/image-button.vue'),
        'user-form': require('components/user/form.vue')
    },
    events: {
        'image:saved': function() {
            console.log('image:saved')
            this.$root.me.fetch();
        }
    },
    props: ['user'],
    methods: {
        toggle: function() {
            this.toggled = !this.toggled;
        },
        save: function(e) {
            if (this.$.form.validate()) {
                var data = this.$.form.serialize();

                this.user.update(data);
                e.preventDefault();

                this.toggled = false;
            }
        }
    }
};
</script>
