var path = require('path');
var webpack = require('webpack');
var js_loader = 'babel?loose=all&nonStandard=false';

module.exports = {
    entry: {
        widgets: './js/widgets.js',
    },
    output: {
        path: path.join(__dirname, 'udata', 'static'),
        publicPath: '/static/',
        filename: 'widgets.js',
    },
    module: {
        loaders: [
            {test: /\.js$/, loader: js_loader},
        ]
    },
    plugins: [
        new webpack.ProvidePlugin({
            'fetch': 'imports?this=>global!exports?global.fetch!whatwg-fetch'
        })
    ]
};
