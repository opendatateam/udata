<!-- User autocompleter -->
<script>
import Vue from 'vue';
import API from 'api';
import BaseCompleter from 'components/form/base-completer.vue';
import placeholders from 'helpers/placeholders';


function render(user, escape) {
    return `<div class="selectize-option">
        <div class="logo pull-left">
            <img src=" ${placeholders.user_avatar(user, 32)} "/>
        </div> ${escape(user.first_name)} ${escape(user.last_name)}
    </div>`;
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
            option: render,
            item: render
        },
    },
    dataLoaded(data) {
        return data.filter(datum => this.userIds.indexOf(datum.id) <= 0);
    },
};
</script>
