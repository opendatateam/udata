import axios from "axios";
import config from "../config";

const CancelToken = axios.CancelToken;
export const generateCancelToken = () => CancelToken.source();

// Instantiate axios with base URL from config
// No need for CSRF or anything fancy here
// TODO : maybe add interceptor to better handle errors ?
const api = axios.create({
  baseURL: config.api_root,
});
const apiv2 = axios.create({
  baseURL: config.api_2_root,
});

export const install = (app) => {
  app.config.globalProperties.$api = api;
  app.config.globalProperties.$apiv2 = apiv2;
};

export default install;
