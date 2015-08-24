define([
    'vue',
    'api',
    'models/dataset',
    'components/form/base-completer.vue',
    'components/dataset/card.vue'
], function(Vue, API, Dataset, BaseCompleter, DatasetCard) {
    'use strict';

    var optTpl = [
            '<div class="selectize-option">',
            '<div class="logo pull-left">',
            '<img src="{{image_url}}"/>',
            '</div>',
            '{{title}}',
            '</div>'
        ].join('');


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

    return {
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
});
