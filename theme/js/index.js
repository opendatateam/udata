import Vue from "vue/dist/vue.js";

import Tabs from "./components/tabs.js";
import Accordion from "./components/accordion";

import Clipboard from "v-clipboard";
import VModal from "vue-js-modal";

import { showModal } from "./components/vue/modals";
import Api from "./plugins/api";
import Auth from "./plugins/auth";

Vue.use(Clipboard);
Vue.use(VModal);
Vue.use(Api);
Vue.use(Auth);

new Vue({
  el: "#app",
  delimiters: ["[[", "]]"],
  methods: {
    showModal
  },
});

console.log("JS is injected !");
