/*
 * Handle i18n loading
 */
import config from "../config";
import { createI18n } from "vue-i18n";

//TODO : use a glob when supported in Parcel 2 : https://github.com/parcel-bundler/parcel/issues/4683
import en from "../locales/en.json";
import fr from "../locales/fr.json"

const missing = (locale, key) => {
  if (key.startsWith("@@")) return key.slice(2);

  console.error(
    "[Dev][i18n] Found translation key not starting with @@",
    locale,
    key
  );
  return key;
};

export default i18n = createI18n({
  locale: config.lang,
  silentTranslationWarn: true,
  missing,
  messages: {
    en,
    fr
  },
});
