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
<box-container title="{{title}}" icon="user" boxclass="user-profile-widget">
    <h3>
        {{user.fullname}}
    </h3>
    <div class="profile-body">
        <image-button src="{{user.avatar}}" size="100" class="avatar-button"
            endpoint="{{endpoint}}">
        </image-button>
        <div v-markdown="{{user.about}}"></div>
    </div>
</box-container>
</template>
<script>
'use strict';

var API = require('api');

module.exports = {
    name: 'user-profile',
    data: function() {
        return {
            title: this._('Profile')
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
        'image-button': require('components/widgets/image-button.vue')
    },
    events: {
        'image:saved': function() {
            console.log('image:saved')
            this.$root.me.fetch();
        }
    },
    props: ['user']
};
</script>
