import RemoveMarkdown from "remove-markdown";

const truncate = (val, length = 300) => {
  if (typeof val !== "string") return;
  return val.length > length ? val.slice(0, length) + "…" : val; //TODO, maybe® : properly truncate words
};

const excerpt = (val, length = 300) => {
  if (typeof val !== "string") return;
  return RemoveMarkdown(truncate(val, length));
};

export const filters = {
  truncate,
  excerpt,
};

//Expose all filters to the app
export default function install(app) {
  app.config.globalProperties.$filters = filters;
}
