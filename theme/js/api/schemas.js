import axios from "axios";
import config from "../config";

/**
 * A schema version.
 * @typedef SchemaVersion
 * @type {object}
 *  @property {string} version_name - The version name, ex: 1.0.0
 *  @property {string} schema_url - The version url
 */

/**
 * A json schema associated with a resource.
 * @typedef Schema
 * @type {object}
 *  @property {string} name - The schema name.
 *  @property {string} schema_type - The schema type.
 *  @property {Array<SchemaVersion>} versions - The schema versions.
 */

let catalog = null;
let catalogRequest = null;

/**
 * Get Schema Catalog
 * @returns {Promise<Array<Schema>>}
 */
export default function getCatalog() {
  if (catalogRequest) {
    return catalogRequest;
  }
  catalogRequest = axios.get(config.schema_catalog_url)
  .then((resp) => resp.data)
  .then((data) => {
    if (data.schemas) {
      catalog = data.schemas;
    }
    return catalog;
  })
  return catalogRequest;
}
