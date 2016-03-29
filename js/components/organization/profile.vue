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
<box :title="_('Profile')" icon="building" boxclass="box-solid org-profile-widget">
    <h3>
        {{org.name}}
        <small v-if="org.acronym">{{org.acronym}}</small>
    </h3>
    <div class="profile-body">
        <image-button :src="org.logo" :size="100" class="logo-button"
            :endpoint="endpoint">
        </image-button>
        <div v-markdown="org.description"></div>
        <div v-if="org.badges | length" class="label-list">
            <strong>
                <span class="fa fa-fw fa-bookmark"></span>
                {{ _('Badges') }}:
            </strong>
            <span v-for="b in org.badges" class="label label-primary">{{badges[b.kind]}}</span>
        </div>
    </div>
</box>
</template>

<script>
import API from 'api';
import Box from 'components/containers/box.vue';
import ImageButton from 'components/widgets/image-button.vue';

export default {
    name: 'org-profile',
    props: {
        org: {
            type: Object,
            required: true
        }
    },
    data: function() {
        return {
            toggled: false,
            badges: require('models/badges').badges.organization
        }
    },
    components: {Box, ImageButton},
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
    }
};
</script>
