/*
 * Handle i18n loading
 */
import config from "../config";
import { createI18n } from "vue-i18n";

//TODO : use a glob when supported in Parcel 2 : https://github.com/parcel-bundler/parcel/issues/4683
import en from "../locales/en.json";

export default i18n = createI18n({
  locale: config.lang,
  silentTranslationWarn: true,
  messages: {
    en,
  },
});
