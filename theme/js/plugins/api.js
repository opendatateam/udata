import axios from "axios";
import config from "../config";

//Instanciate axios with base URL from config
const api = axios.create({
  baseURL: config.api_root,
});

//TODO, probably : add interceptors to add CSRF info and credentials

export const install = (Vue) => {
  Vue.prototype.$api = Vue.api = api;
};

export default install;
