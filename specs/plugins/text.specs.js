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
            expect(t.$el).to.contain.text('Text should be…');
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

    describe('Size filter', function() {
        it('Should display Bytes', function() {
            const size = tester('10', 'size');
            expect(size.$el).to.contain.text('10 Bytes');
        });

        it('Should until to Bytes at 1023 Bytes', function() {
            const size = tester('1023', 'size');
            expect(size.$el).to.contain.text('1023 Bytes');
        });

        it('Should transform to KiloBytes at 1024 Bytes', function() {
            const size = tester('1024', 'size');
            expect(size.$el).to.contain.text('1.0 KB');
        });

        it('Should round to KiloBytes after 1024 Bytes', function() {
            const size = tester('2150', 'size');
            expect(size.$el).to.contain.text('2.1 KB');
        });

        it('Should transform to MegaBytes at 2^20 Bytes', function() {
            const size = tester('1048576', 'size');
            expect(size.$el).to.contain.text('1.0 MB');
        });

        it('Should round to MegaBytes after 2^20 Bytes', function() {
            const size = tester('2150000', 'size');
            expect(size.$el).to.contain.text('2.1 MB');
        });

        it('Should transform to GigaBytes at 2^30 Bytes', function() {
            const size = tester('1073741824', 'size');
            expect(size.$el).to.contain.text('1.0 GB');
        });

        it('Should transform to TeraBytes at 2^40 Bytes', function() {
            const size = tester('1099511628000', 'size');
            expect(size.$el).to.contain.text('1.0 TB');
        });
    });
});
