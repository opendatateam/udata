import { createApp } from "vue";

import Threads from "./components/discussions/threads.vue";

import Tabs from "./components/vanilla/tabs";
import Accordion from "./components/vanilla/accordion";

import VueClipboard from "vue3-clipboard";
// import VModal from "vue-js-modal";
// import Toast from "vue-toasted";

// import { showModal } from "./plugins/modals";
import Api from "./plugins/api";
import Auth from "./plugins/auth";
// import i18n from "./plugins/i18n";

const app = createApp({});

app.use(VueClipboard, {
  autosetContainer: true
});
// app.use(VModal);
// app.use(Toast);
// app.use(i18n);
app.use(Api);
app.use(Auth);

app.component("discussion-threads", Threads);
// app.component(showModal);

app.mount('#app');

console.log("JS is injected !");
