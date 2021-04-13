export const filters = {
  truncate(val, length = 300) {
    if (typeof val !== "string") return;
    return val.length > length ? val.slice(0, length) + "…" : val; //TODO, maybe® : properly truncate words
  },
};

//Expose all filters to the app
export default function install(app) {
  app.config.globalProperties.$filters = filters;
}
