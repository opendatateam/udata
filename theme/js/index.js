import Vue from "vue/dist/vue.js";

import Tabs from "./components/vanilla/tabs";
import Accordion from "./components/vanilla/accordion";

import Threads from "./components/discussions/threads.vue";

import Clipboard from "v-clipboard";
import VModal from "vue-js-modal";
import Toast from "vue-toasted";

import { showModal } from "./plugins/modals";
import Api from "./plugins/api";
import Auth from "./plugins/auth";

Vue.use(Clipboard);
Vue.use(VModal);
Vue.use(Toast);
Vue.use(Api);
Vue.use(Auth);

new Vue({
  el: "#app",
  delimiters: ["[[", "]]"],
  components: {
    "discussion-threads": Threads,
  },
  methods: {
    showModal,
  },
});

console.log("JS is injected !");
