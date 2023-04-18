<script>
import Vue from 'vue';
import API from 'api';
import Reuse from 'models/reuse';
import BaseCompleter from 'components/form/base-completer.vue';
import ReuseCard from 'components/reuse/card.vue';


function render(data, escape) {
    return `<div class="selectize-option">
        <div class="logo pull-left">
            <img src=" ${data.image_url} "/>
        </div>
        ${escape(data.title)}
    </div>`;
}

function cardify(value, $el) {
    var card = new Vue({
            el: $el[0],
            mixins: [ReuseCard]
        }),
        $btn = $el.find('.remove');
    card.reuse.fetch(value);
    $el.append($btn);
}

export default {
    mixins: [BaseCompleter],
    ns: 'reuses',
    endpoint: 'suggest_reuses',
    props: {
        placeholder: {
            type: String,
            default: function() {return this._('Find your reuse');}
        }
    },
    selectize: {
        plugins: ['remove_button'],
        valueField: 'id',
        labelField: 'title',
        searchField: ['title'],
        onItemAdd: cardify,
        onInitialize: function() {
            this.$control.find('.card-input').each(function(card) {
                var $this = $(this);
                cardify($this.data('value'), $this);
            });
        },
        render: {
            option: render,
            item: function(data, escape) {
                return `<div class="card-input">${escape(data.title)}</div>`;
            }
        }
    }
};
</script>
