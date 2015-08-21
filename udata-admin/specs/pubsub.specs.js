import {PubSub, pubsub} from 'pubsub';

describe("PubSub", function() {

    it('have an empty topic list on instanciation', function() {
        expect(new PubSub()).to.have.property('topics').to.be.empty;
    });

    it('handle topic subscription', function() {
        let p = new PubSub(),
            callback = function() {};

        p.subscribe('test', callback);
        expect(p.topics).to.have.property('test').to.contain(callback);
    });

    it('return a remove handle on subscription', function() {
        let p = new PubSub(),
            callback = function() {},
            handle = p.subscribe('test', callback);

        expect(handle).to.have.property('remove');
        expect(p.topics.test).to.have.length(1);

        handle.remove();

        expect(p.topics.test).not.to.contain(callback);
    });

    it('allows to test topic existence', function() {
        let p = new PubSub();

        p.subscribe('test', function() {});

        expect(p.has('test')).to.be.true;
        expect(p.has('unknown')).to.be.false;
    });

    it('handle topic unsubscription', function() {
        let p = new PubSub(),
            callback = function() {};

        p.subscribe('test', callback);
        expect(p.topics).to.have.property('test').to.contain(callback);

        p.unsubscribe('test', callback);
        expect(p.topics.test).not.to.contain(callback);
    });

    it('expose a global pubsub instance', function() {
        expect(pubsub).to.be.an.instanceof(PubSub);
    });

    it('calls all subscribed handlers', function() {
        let p = new PubSub(),
            callback = sinon.spy(),
            callback2 = sinon.spy();

        p.subscribe('test', callback);
        p.subscribe('test', callback2);

        p.publish('test', 'value1', 'value2');

        expect(callback).to.have.been.calledWith('value1', 'value2');
        expect(callback2).to.have.been.calledWith('value1', 'value2');
    });

    it('does not call unsubscribed handlers', function() {
        let p = new PubSub(),
            callback = sinon.spy(),
            callback2 = sinon.spy();

        p.subscribe('test', callback);
        p.subscribe('test', callback2);

        p.unsubscribe('test', callback);

        p.publish('test');

        expect(callback).not.to.have.been.called;
        expect(callback2).to.have.been.called;
    });

    it('allows to subscribe once', function() {
        let p = new PubSub(),
            callback = sinon.spy();

        p.once('test', callback);

        p.publish('test');
        p.publish('test');

        expect(callback).to.have.been.calledOnce;
    });

    it('allows to remove a topic', function() {
        let p = new PubSub();

        p.subscribe('test', function() {});
        expect(p.has('test')).to.be.true;

        p.remove('test')
        expect(p.has('test')).to.be.false;
    });

});
