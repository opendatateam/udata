<script>
import Vue from 'vue';
import API from 'api';
import Dataset from 'models/dataset';
import BaseCompleter from 'components/form/base-completer.vue';
import DatasetCard from 'components/dataset/card.vue';

const optTpl = `<div class="selectize-option">
    <div class="logo pull-left">
        <img src="{{image_url}}"/>
    </div>
    {{title}}
</div>`;


function cardify(value, $el) {
    if (value && $el.length > 0) {
        var dataset = new Dataset().fetch(value),
            card = new Vue({
                el:$el[0],
                mixins: [DatasetCard],
                data: {dataset: dataset}
            }),
            $btn = $el.find('.remove');
        $el.append($btn);
    }
}

export default {
    name: 'dataset_completer',
    mixins: [BaseCompleter],
    ns: 'datasets',
    endpoint: 'suggest_datasets',
    data: function() {
        return {
            placeholder: this._('Find your dataset')
        };
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
            option: function(data, escape) {
                return new Vue({data: data}).$interpolate(optTpl);
            },
            item: function(data, escape) {
                return '<div class="card-input">'+data.title+'</div>';
            }
        },
    }
};
</script>
