describe("Markdown plugin", function() {
    var Vue = require('vue');

    Vue.use(require('plugins/markdown'));
    Vue.config.async = false;

    afterEach(function() {
        fixture.cleanup();
    });

    function strip(el) {
        $(el).contents().each(function(index, node) {
            if (node.nodeType == Node.COMMENT_NODE) {
                $(node).remove();
            }
        });
        return el;
    }

    describe("markdown filter", function() {

        var Tester = Vue.extend({
                template: '{{{text | markdown}}}'
            });

        function el(text) {
            var vm = new Tester({
                    el: fixture.set('<div/>')[0],
                    replace: false,
                    data: {
                        text: text
                    }
                });
            return $(strip(vm.$el));
        }

        it('should render falsy values as ""', function() {
            expect(el('').is(':empty')).to.be.true;
            expect(el(null).is(':empty')).to.be.true;
            expect(el(undefined).is(':empty')).to.be.true;
        });

        it('should markdown content', function() {
            expect(el('aaa')).to.have.html('<p>aaa</p>');
            expect(el('**aaa**')).to.have.html('<p><strong>aaa</strong></p>');
        });
    });

    describe("markdown directive", function() {

        var Tester = Vue.extend({
                template: '<div id="markdown" v-markdown="{{text}}"></div>'
            });

        function el(text) {
            var vm = new Tester({
                    el: fixture.set('<div/>')[0],
                    replace: false,
                    data: {
                        'text': text
                    }
                }),
                div = $(vm.$el).find('#markdown')[0];
            return $(strip(div));
        }

        it('should render falsy values as ""', function() {
            expect(el('').is(':empty')).to.be.true;
            expect(el(null).is(':empty')).to.be.true;
            expect(el(undefined).is(':empty')).to.be.true;
        });

        it('should markdown content', function() {
            expect(el('**aaa**')).to.have.html('<p><strong>aaa</strong></p>\n');
            expect(el('aaa')).to.have.html('<p>aaa</p>\n');
        });
    });

});
