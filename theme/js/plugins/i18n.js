/*
 * Handle i18n loading
 */
import config from "../config";
import VueI18n from "vue-i18n";

//TODO : use a glob when supported in Parcel 2 : https://github.com/parcel-bundler/parcel/issues/4683
import fr from "../locales/fr.json";
import en from "../locales/en.json";

export default function install(Vue) {
  Vue.use(VueI18n);

  const i18n = new VueI18n({
    locale: config.lang,
    messages: {
      en,
      fr
    }
  })

  //Globally register '_' translation fn
  Vue.prototype._ = i18n;
}
