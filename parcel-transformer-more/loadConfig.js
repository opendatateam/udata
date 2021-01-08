// @flow
const path = require('path');

exports.load = async function load({config}) {
  let configFile = await config.getConfig(['.lessrc', '.lessrc.js'], {
    packageKey: 'less',
  });

  let configContents = {};
  if (configFile != null) {
    configContents = configFile.contents;
  }

  // Rewrites urls to be relative to the provided filename
  configContents.rewriteUrls = 'all';
  configContents.plugins = configContents.plugins || [];

  // This should enforce the config to be reloaded on every run as it's JS
  let isDynamic = configFile && path.extname(configFile.filePath) === '.js';
  if (isDynamic) {
    config.shouldInvalidateOnStartup();
    config.shouldReload();
  }

  return config.setResult({isStatic: !isDynamic, config: configContents});
}

exports.preSerialize = function(config) {
  if (!config.result) return;

  // Ensure we dont pass functions to the serialiser
  if (!config.result.isStatic) {
    config.result.config = {};
  }
}
