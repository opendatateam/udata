const path = require('path');

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
            {
                test: /\.js$/,
                loader: 'babel-loader',
                query: {
                    presets: ['es2015'],
                    comments: false
                }
            },
        ]
    }
};
