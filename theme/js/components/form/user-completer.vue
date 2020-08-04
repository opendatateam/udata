<!-- User autocompleter -->
<script>
import Vue from 'vue';
import API from 'api';
import BaseCompleter from 'components/form/base-completer.vue';

const template = `<div class="selectize-option">
    <div class="logo pull-left">
        <img src="{{ user | avatar_url 32 }}"/>
    </div>
    {{user.first_name}} {{user.last_name}}
</div>`;


function render(user) {
    return new Vue({data: {user: user}}).$interpolate(template);
}

export default {
    mixins: [BaseCompleter],
    ns: 'users',
    endpoint: 'suggest_users',
    selectize: {
        valueField: 'id',
        searchField: ['first_name', 'last_name'],
        options: [],
        plugins: ['remove_button'],
        render: {
            option: (data, escape) => render(data),
            item: (data, escape) => render(data)
        },
    },
    dataLoaded(data) {
        return data.filter(datum => this.userIds.indexOf(datum.id) <= 0);
    },
};
</script>
