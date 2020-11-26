import axios from "axios";
import config from "../config";

//Instanciate axios with base URL from config
//No need for CSRF or anything fancy here
//TODO : maybe add interceptor to better handle errors ?
const api = axios.create({
  baseURL: config.api_root,
});

export const install = (Vue) => {
  Vue.prototype.$api = Vue.api = api;
};

export default install;
