var webpack = require('webpack');
var config = require('./webpack.widgets.config');

config.plugins.push(new webpack.optimize.UglifyJsPlugin({
    minimize: true,
    output: {comments: false},
    compress: {
        warnings: true
    }
}));

config.devtool = 'source-map';

module.exports = config;
