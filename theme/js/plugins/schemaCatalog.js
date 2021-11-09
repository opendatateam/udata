import axios from "axios";
import config from "../config";
import {generateCancelToken} from "./api";

let catalog = null;
let catalogRequest = null;

function getCatalog() {
  if(catalog) {
    return catalog;
  }
  if (catalogRequest) {
    catalogRequest.cancel();
  }
  catalogRequest = generateCancelToken();
  return axios.get(config.schema_catalog_url, {
    cancelToken: catalogRequest.token,
  })
  .then((resp) => resp.data)
  .then((data) => {
    if (data.schemas) {
      catalog = data.schemas;
    }
    return catalog;
  })
  .catch(error => {
    // TODO: use toaster to show an error when v1.3 is on NPM and js usage is available
    console.log(error)
  });
}

export default function install(app) {
  app.config.globalProperties.$getSchemaCatalog = getCatalog;
}
