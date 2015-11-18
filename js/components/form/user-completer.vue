<!-- User autocompleter -->
<script>
import Vue from 'vue';
import API from 'api';
import BaseCompleter from 'components/form/base-completer.vue';
import placeholders from 'helpers/placeholders';

const template = `<div class="selectize-option">
    <div class="logo pull-left">
        <img :src="user.avatar || user.avatar_url || placeholder"/>
    </div>
    {{user.first_name}} {{user.last_name}}
</div>`;


function render(user) {
    return new Vue({data: {user: user, placeholder: placeholders.user}}).$interpolate(template);
}

export default {
    name: 'user_completer',
    mixins: [BaseCompleter],
    ns: 'users',
    endpoint: 'suggest_users',
    selectize: {
        valueField: 'id',
        searchField: ['first_name', 'last_name'],
        options: [],
        plugins: ['remove_button'],
        render: {
            option: function(data, escape) {
                return render(data);
            },
            item: function(data, escape) {
                return render(data);
            }
        },
    },
    dataLoaded: function(data) {
        return data.filter((datum) => {
            return this.userIds.indexOf(datum.id) <= 0;
        });
    },
};
</script>
