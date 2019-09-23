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
<div>
<box :title="title" icon="user" boxclass="user-profile-widget">
    <h3>{{user.fullname}}</h3>
        <div class="profile-body">
            <image-button :src="user | avatar_url 100" :size="100" class="avatar-button"
                :endpoint="endpoint" :editable="can_edit">
            </image-button>
        <div v-markdown="user.about"></div>
    </div>
</box>
</div>
</template>

<script>
import API from 'api';
import Box from 'components/containers/box.vue';
import ImageButton from 'components/widgets/image-button.vue';

export default {
    name: 'user-profile',
    props: ['user'],
    data() {
        return {
            title: this._('Profile'),
        };
    },
    computed: {
        endpoint() {
            var operation = API.me.operations.my_avatar;
            return operation.urlify({});
        },
        can_edit() {
            return this.$root.me.is_admin || this.user.id == this.$root.me;
        }
    },
    components: {Box, ImageButton},
    events: {
        'image:saved': function() {
            this.user.fetch();
        }
    },
};
</script>
