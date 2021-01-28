import { createApp } from "vue";

import Threads from "./components/discussions/threads.vue";
import Search from "./components/search/search";

import Tabs from "./components/vanilla/tabs";
import Accordion from "./components/vanilla/accordion";

import VueClipboard from "vue3-clipboard";
import VueFinalModal from "vue-final-modal";
import Toaster from "@meforma/vue-toaster";

import Api from "./plugins/api";
import Auth from "./plugins/auth";
import Modals from "./plugins/modals";
import i18n from "./plugins/i18n";

const app = createApp({});

app.use(VueClipboard, {});
app.use(Api);
app.use(Auth);
app.use(VueFinalModal());
app.use(Modals); //Has to be loaded after VueFinalModal
app.use(i18n);
app.use(Toaster);

app.component("discussion-threads", Threads);
app.component("search", Search);

app.mount("#app");

console.log("JS is injected !");
