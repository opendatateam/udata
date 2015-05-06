define([
    'vue',
    'api',
    'models/reuse',
    'components/form/base-completer.vue',
    'components/reuse/card.vue'
], function(Vue, API, Reuse, BaseCompleter, ReuseCard) {
    'use strict';

    var optionTpl = [
            '<div class="selectize-option">',
                '<div class="logo pull-left">',
                    '<img src="{{image_url}}"/>',
                '</div>',
                '{{title}}',
            '</div>'
        ].join('');

    function cardify(value, $el) {
        var reuse = new Reuse().fetch(value),
            card = new Vue({
                mixins: [ReuseCard],
                data: {reuse: reuse}
            }),
            $btn = $el.find('.remove');
        card.$mount($el[0]);
        $el.append($btn);
    }

    return {
        name: 'reuse_completer',
        mixins: [BaseCompleter],
        ns: 'reuses',
        endpoint: 'suggest_reuses',
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
                option: function(data, escape) {
                    return new Vue({data: data}).$interpolate(optionTpl);
                },
                item: function(data, escape) {
                    return '<div class="card-input">'+data.title+'</div>';
                }
            }
        }
    };
});
