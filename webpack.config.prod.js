var webpack = require("webpack"),
    config = require('./webpack.config');

config.plugins.push(new webpack.optimize.UglifyJsPlugin({
    minimize: true,
    output: {comments: false},
    mangle: false,
    compress: {
        warnings: false
    }
}));

config.devtool = 'source-map';

config.plugins.push(new webpack.optimize.DedupePlugin());
config.plugins.push(new webpack.optimize.OccurenceOrderPlugin(true));

/**
 * Image optimization.
 * Not working yet
 */
// config.module.loaders.push({
//     test: /^images\/.*\.(jpe?g|png|gif|svg)$/i,
//     loaders: ['image?bypassOnDebug&optimizationLevel=7&interlaced=false']
// });

module.exports = config;
