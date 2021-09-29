import mitt from "mitt";

const emitter = mitt();

// emitter.on("*", (type, e) => console.log(type, e));

export const install = (app) => {
  app.config.globalProperties.$bus = emitter;
};

export default install;
