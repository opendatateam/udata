<template>
<box id="apikey" title="{{ _('API Key') }}" footer="{{true}}" icon="key" class="apikey">
    <p>{{ _('This widget allows you to generate or regenerate your API Key.') }}</p>
    <p>{{ _('This key is needed if you want to use the API.') }}</p>
    <div>
        <textarea v-if="user.apikey" class="form-control" rows="2" readonly>{{user.apikey}}</textarea>
        <p v-if="!user.apikey" class="form-control-static">{{ _("You don't have generated an API KEY yet.") }}</p>
    </div>
    <footer>
        <button v-if="user.apikey" class="btn btn-default"
            v-on="click: generate">{{ _('Regenerate') }}</button>
        <button v-if="user.apikey" class="btn btn-warning"
            v-on="click: clear">{{ _('Clear') }}</button>
        <button v-if="!user.apikey" class="btn btn-default"
            v-on="click: generate">{{ _('Generate an API KEY') }}</button>
    </footer>
</box>
</template>

<script>
import User from 'models/user';
import API from 'api';

export default {
    props: ['user'],
    data: function() {
        return {
            user: new User()
        };
    },
    components: {
        box: require('components/containers/box.vue')
    },
    methods: {
        generate: function() {
            API.me.generate_apikey({}, (response) => {
                this.user.apikey = response.obj.apikey;
            });
        },
        clear: function() {
            API.me.clear_apikey({}, (response) => {
                this.user.apikey = null;
            });
        }
    }
};
</script>
