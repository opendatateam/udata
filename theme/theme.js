require('./less/gouvfr.less');

// Ensure all images are copied
require.context('./img', true, /^\.\/.*\.(jpg|jpeg|png|gif|svg)$/);
