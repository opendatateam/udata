<script>
import Vue from 'vue';
import API from 'api';
import Dataset from 'models/dataset';
import BaseCompleter from 'components/form/base-completer.vue';
import DatasetCard from 'components/dataset/card.vue';

function render(data, escape) {
    return `<div class="selectize-option">
        <div class="logo pull-left">
            <img src=" ${data.image_url} "/>
        </div>
        ${escape(data.title)}
    </div>`;
}


function cardify(value, $el) {
    if (value && $el.length > 0) {
        var card = new Vue({
                el:$el[0],
                mixins: [DatasetCard]
            }),
            $btn = $el.find('.remove');
        card.dataset.fetch(value);
        $el.append($btn);
    }
}

export default {
    name: 'dataset-completer',
    mixins: [BaseCompleter],
    ns: 'datasets',
    endpoint: 'suggest_datasets',
    props: {
        placeholder: {
            type: String,
            default: function() {return this._('Find your dataset');}
        }
    },
    selectize: {
        valueField: 'id',
        labelField: 'title',
        searchField: ['title'],
        options: [],
        plugins: ['remove_button'],
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
        },
    }
};
</script>
