import fixtures from 'js-fixtures';

export function set(text) {
    fixtures.set(text);
    return fixtures.window().document.body.firstChild;
};

export function cleanup() {
    fixtures.cleanUp();
};
