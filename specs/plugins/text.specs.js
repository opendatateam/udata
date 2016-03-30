describe('Text plugin', function() {
    const Vue = require('vue');

    Vue.use(require('plugins/text'));
    Vue.config.async = false;


    afterEach(function() {
        fixture.cleanup();
    });

    function tester(text, filter) {
        return new Vue({
            el: fixture.set(`<div>{{ text | ${filter} }}</div>`)[0],
            data: {
                text: text
            }
        });
    }

    describe('truncate filter', function() {
        it('should truncate a string and add an ellipsis', function() {
            const t = tester('Text should be truncated', 'truncate 15');
            expect(t.$el).to.contain.text('Text should ...');
        });

        it('should not truncate if string is smaller', function() {
            const t = tester('untruncated', 'truncate 15');
            expect(t.$el).to.contain.text('untruncated');
        });
    });

    describe('Title filter', function() {
        it('Should upper the first chars of a single lower word', function() {
            const lower = tester('lower', 'title');
            expect(lower.$el).to.contain.text('Lower');
        });

        it('Should upper the first chars of a single upper word', function() {
            const upper = tester('UPPER', 'title');
            expect(upper.$el).to.contain.text('Upper');
        });

        it('Should upper the first chars of each word', function() {
            const upper = tester('UPPER word', 'title');
            expect(upper.$el).to.contain.text('Upper Word');
        });
    });
});
