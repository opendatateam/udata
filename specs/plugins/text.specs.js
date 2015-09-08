describe("Text plugin", function() {
    var Vue = require('vue');

    Vue.use(require('plugins/text'));
    Vue.config.async = false;


    afterEach(function() {
        fixture.cleanup();
    });

    var Tester = Vue.extend({
        template: '{{text | truncate 15}}'
    });

    function tester(text, filter) {
        return new Tester({
            el: fixture.set('<div/>'),
            replace: false,
            data: {
                text: text
            },
            template: '{{text | ' + filter + '}}'
        });
    }

    describe("truncate filter", function() {
        it('should truncate a string and add an ellipsis', function() {
            var t = tester('Text should be truncated', 'truncate 15');
            expect($(t.$el)).to.contain('Text should ...');
        });

        it('should not truncate if string is smaller', function() {
            var t = tester('untruncated', 'truncate 15');
            expect($(t.$el)).to.contain('untruncated');
        });
    });

    describe('Title filter', function() {
        it('Should upper the first chars of a single word', function() {
            var t = tester('lower', 'title');
            expect($(t.$el)).to.contain('Lower');

            var t = tester('UPPER', 'title');
            expect($(t.$el)).to.contain('Upper');
        });

        it('Should upper the first chars of each word', function() {
            var t = tester('lower word', 'title');
            expect($(t.$el)).to.contain('Lower Word');

            var t = tester('UPPER word', 'title');
            expect($(t.$el)).to.contain('Upper Word');
        });
    })

});
