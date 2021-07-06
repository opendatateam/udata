import { createApp } from "vue";

import Threads from "./components/discussions/threads.vue";
import Suggest from "./components/search/suggest-box";
import Search from "./components/search/search";
import FollowButton from "./components/utils/follow-button";

import Tabs from "./components/vanilla/tabs";
import Accordion from "./components/vanilla/accordion";
import Clipboard from "./components/vanilla/clipboard";

import VueFinalModal from "vue-final-modal";
import Toaster from "@meforma/vue-toaster";

import Api from "./plugins/api";
import Auth from "./plugins/auth";
import Modals from "./plugins/modals";
import i18n from "./plugins/i18n";
import filters from "./plugins/filters";

const app = createApp({});

app.use(Api);
app.use(Auth);
app.use(VueFinalModal());
app.use(Modals); //Has to be loaded after VueFinalModal
app.use(i18n);
app.use(filters);
app.use(Toaster);

app.component("discussion-threads", Threads);
app.component("suggest", Suggest);
app.component("search", Search);
app.component("follow-button", FollowButton);

app.mount("#app");

console.log("JS is injected !");
