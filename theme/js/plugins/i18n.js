/*
 * Handle i18n loading
 */
import config from "../config";
import VueI18n from "vue-i18n";

import messages from "../locales/*.json";

export default function install(Vue) {
  Vue.use(VueI18n);

  const i18n = new VueI18n({
    locale: config.lang,
    messages
  })

  //Globally register '_' translation fn
  Vue.prototype._ = i18n;
}
