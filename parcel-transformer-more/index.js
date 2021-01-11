// @flow
const Less = require('less');
const path = require('path');
const {Transformer} = require('@parcel/plugin');
const SourceMap = require('@parcel/source-map').default;

const {load, preSerialize} = require('./loadConfig');

// E.g: ~library/file.less
const WEBPACK_ALIAS_RE = /^~[^/]/;

exports.default = (new Transformer({
  loadConfig({config}) {
    return load({config});
  },

  preSerializeConfig({config}) {
    return preSerialize(config);
  },

  async transform({asset, options, config, resolve, logger}) {
    asset.type = 'css';
    asset.meta.hasDependencies = false;

    let less = await options.packageManager.require('less', asset.filePath, {
      shouldAutoInstall: options.shouldAutoInstall,
    });

    let code = await asset.getCode();
    let result;
    try {
      let lessConfig = config ? {...config.config} : {};

      if (asset.env.sourceMap) {
        lessConfig.sourceMap = {};
      }

      lessConfig.filename = asset.filePath;
      lessConfig.plugins = [
        ...(lessConfig.plugins || []),
        urlPlugin({asset}),
        resolvePathPlugin({asset, resolve}),
      ];

      result = await less.render(code, lessConfig);
    } catch (err) {
      // For the error reporter
      err.fileName = err.filename;
      err.loc = {
        line: err.line,
        column: err.column,
      };
      throw err;
    }

    if (result.map != null) {
      let map = new SourceMap(options.projectRoot);
      let rawMap = JSON.parse(result.map);
      map.addRawMappings({
        ...rawMap,
        sources: rawMap.sources.map(s => path.relative(options.projectRoot, s)),
      });
      asset.setMap(map);

      for (let source of rawMap.sources) {
        if(source !== asset.filePath)
          await asset.addIncludedFile(source)
      }
    }

    asset.setCode(result.css);

    return [asset];
  },
}));

function urlPlugin({asset}) {
  return {
    install(less, pluginManager) {
      const visitor = new less.visitors.Visitor({
        visitUrl(node) {
          const valueNode = node.value
          const stringValue = valueNode.value
          if (
            !stringValue.startsWith('#') // IE's `behavior: url(#default#VML)`)
          ) {
            valueNode.value = asset.addURLDependency(stringValue, {});
          }
          return node;
        },
      });

      visitor.run = visitor.visit;
      pluginManager.addVisitor(visitor);
    },
  };
}

function resolvePathPlugin({asset, resolve}) {
  return {
    install(less, pluginManager) {
      class LessFileManager extends less.FileManager {
        supports() {
          return true;
        }

        supportsSync() {
          return false;
        }

        async loadFile(rawFilename, ...args) {
          let filename = rawFilename;

          if (WEBPACK_ALIAS_RE.test(filename)) {
            let correctPath = filename.replace(/^~/, '');
            throw new Error(
              `The @import path "${filename}" is using webpack specific syntax, which isn't supported by Parcel.\n\nTo @import files from node_modules, use "${correctPath}"`,
            );
          }

          try {
            return await super.loadFile(filename, ...args);
          } catch (err) {
            if (err.type !== 'File') {
              throw err;
            }
            filename = await resolve(asset.filePath, filename);
            return super.loadFile(filename, ...args);
          }
        }
      }

      pluginManager.addFileManager(new LessFileManager());
    },
  };
}
