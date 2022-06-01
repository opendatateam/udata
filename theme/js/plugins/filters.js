import RemoveMarkdown from "remove-markdown";
import config from "../config";
import dayjs from "dayjs";
import markdown from "../markdown";
import "dayjs/locale/fr";
import "dayjs/locale/en";
import "dayjs/locale/es";
import LocalizedFormat from 'dayjs/plugin/localizedFormat'

dayjs.extend(LocalizedFormat);
dayjs.locale(config.lang);

const truncate = (val, length = 300) => {
  if (typeof val !== "string") return;
  return val.length > length ? val.slice(0, length) + "…" : val; //TODO, maybe® : properly truncate words
};

const excerpt = (val, length = 300) => {
  if (typeof val !== "string") return;
  return truncate(RemoveMarkdown(val), length);
};

const filesize = (val) => {
    const suffix = 'o'
    const units = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']
    for (let unit of units) {
        if (Math.abs(val) < 1024.0) {
          return `${val.toFixed(1)}${unit}${suffix}`
        }
        val /= 1024.0
    }
    return `${val.toFixed(1)}Y${suffix}`
}

const formatDate = (date, format = 'LL') => {
  return dayjs(date).format(format);
}

export const filters = {
  truncate,
  excerpt,
  filesize,
  formatDate,
  markdown,
};

// Expose all filters to the app
export default function install(app) {
  app.config.globalProperties.$filters = filters;
  app.provide('$filters', app.config.globalProperties.$filters);
}
