// Stolen from https://github.com/aickin/react-server/blob/master/packages/react-server-cli/src/NonCachingExtractTextLoader.js
// via https://github.com/webpack/extract-text-webpack-plugin/issues/42#issuecomment-187296362

var ExtractTextLoader = require('extract-text-webpack-plugin/loader');

module.exports = function(source) {
    this.cacheable = false;
    return ExtractTextLoader.call(this, source);
}

module.exports.pitch = function(request) {
    this.cacheable = false;
    return ExtractTextLoader.pitch.call(this, request);
}
