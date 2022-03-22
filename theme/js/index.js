import { createApp } from "vue";

import Threads from "./components/discussions/threads.vue";
import Suggest from "./components/search/suggest-box";
import Search from "./components/search/search";
import FeaturedButton from './components/utils/featured';
import FollowButton from "./components/utils/follow-button";
import ReadMore from "./components/utils/read-more";
import RequestMembership from "./components/organization/request-membership";
import Resources from "./components/dataset/resource/resources.vue";
import SearchBar from "./components/utils/search-bar.vue";
import * as dsfr from "@gouvfr/dsfr/dist/dsfr/dsfr.module";

import Tabs from "./components/vanilla/tabs";
import Accordion from "./components/vanilla/accordion";
import Clipboard from "./components/vanilla/clipboard";

import VueFinalModal from "vue-final-modal";
import Toaster from "@meforma/vue-toaster";

import Api from "./plugins/api";
import EventBus from "./plugins/eventbus";
import Auth from "./plugins/auth";
import Modals from "./plugins/modals";
import i18n from "./plugins/i18n";
import bodyClass from "./plugins/bodyClass";
import filters from "./plugins/filters";

import InitSentry from "./sentry";

/**
 * @interface Ref
 * @template T
 * @property {T} value
 */

/**
 * @typedef {Object} Ref
 * @property value - The referenced value
*/

const configAndMountApp = (el) => {
  const app = createApp({});

  // Configure as early as possible in the app's lifecycle
  InitSentry(app);

  app.use(Api);
  app.use(EventBus);
  app.use(Auth);
  app.use(VueFinalModal());
  app.use(Modals); //Has to be loaded after VueFinalModal
  app.use(i18n);
  app.use(bodyClass);
  app.use(filters);
  app.use(Toaster).provide('toast', app.config.globalProperties.$toast);

  app.component("discussion-threads", Threads);
  app.component("suggest", Suggest);
  app.component("search", Search);
  app.component("follow-button", FollowButton);
  app.component("featured-button", FeaturedButton);
  app.component("read-more", ReadMore);
  app.component("request-membership", RequestMembership);
  app.component("dataset-resources", Resources);
  app.component("search-bar", SearchBar);

  // unset delimiters used in html templates to prevent injections using {{ }}
  app.config.compilerOptions.delimiters = [];

  const vm = app.mount(el);
};

const elements = document.querySelectorAll(".vuejs");

elements.forEach((el) => {
  //We keep the div HTML from before trying to mount the VueJS App
  const previousHtml = el.innerHTML;

  try {
    configAndMountApp(el);
  } catch (e) {
    //If the mount wasn't successful, Vue will remove all HTML from the div. We'll put it back so you can use the website.
    el.innerHTML = previousHtml;

    console.log(
      `VueJS template compilation failed for element ${el.className}.
      Aborted the process and rolled back the HTML.
      See error(s) above and below (probably won't help you tho) :`
    );
    console.log(el);
    console.error(e);
    throw e;
  }
});

console.log("JS is injected !");
