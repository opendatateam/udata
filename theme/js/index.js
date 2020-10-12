import Vue from "vue/dist/vue.js";
import Tabs from "./components/tabs.js";
import Accordion from "./components/accordion";

import Clipboard from "v-clipboard";

Vue.use(Clipboard);

new Vue({
  el: "#app",
  components: { },
  delimiters: ['[[', ']]']
});

console.log("JS is injected !");
