//Small helpers to add and remove classes from the body tag
export default function install(app) {
  app.config.globalProperties.addBodyClass = (className) =>
    document.body.classList.add(className);
  app.config.globalProperties.removeBodyClass = (className) =>
    document.body.classList.remove(className);
}
