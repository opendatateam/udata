/*
---
name: Modals
category: 5 - Interactions
---

# Modals
Because sometimes the whole page isn't enough to show all the data you want to show to the world.

You can define modal templates in the form of VueJS templates and call them anywhere within the site.

1. Defining a modal
Modals are defined in the `theme/js/components/**` folder. You'll find an example below.
Note that you can define variables in the `props` part of the Vue template definition and pass them to the modal later on.

```modals-definition.vue
<template>
  <div class="modal-wrapper">
    <div class="modal-body">
      <iframe :src="url" width="100%" height="600" frameborder="0"></iframe>
    </div>

    <footer class="modal-footer">
      <button class="fr-btn fr-fi-close-line" @click.prevent="$emit('close')"> {{$t('Close')}} </button>
    </footer>
  </div>
</template>

<script>
export default {
  name: "Preview",
  props: {
      url: String
  }
};
</script>
```

2. Modal registration
Once you defined your modal, you need to import it inside the js package in the `theme/js/components/vue/modals.js` component.
The `modals` object lists all the available modal. The key you'll give in this object will be the modal's name, required when you'll want to open it.

```modal-registration.js
import MyModal from "./myModal";

const modals = { preview: Preview, mymodal: MyModal };
```


## Opening a modal
To open a modal, simply call the global `showModal` method with your modal name as seen above.
The first argument is the modal name, the second one is an object containing the params passed to the modal.
The third argument to the `showModal` method is an override for the `scrollable` property. Defaults to false, but when set to true, the modal is scrollable.

You should also add a `<modals-container></modals-container>` element that will host the modal DOM inside the same VueJS app.

```modal-opening.html
<span class="vuejs">
  <modals-container></modals-container>
  <a @click.prevent="$showModal('mymodal', {myparam: '{{ django.injected_param }}'}, true)">Click me !</a>
</span>
```
*/

import Preview from "../components/dataset/preview.vue";
import Schema from "../components/dataset/schema-modal.vue";

const modals = { preview: Preview, schema: Schema };

const _showModal = (app) => (name, params) => {
  const Vue = app.config.globalProperties;

  Vue.$vfm.show({
    component: modals[name],
    bind: {
      name,
      escToClose: true,
      lockScroll: true,
      ...params,
      close: () => Vue.$vfm.hide(name),
    },
  });
};

export default function install(app) {
  app.config.globalProperties.$showModal = _showModal(app);
  app.provide('$showModal', app.config.globalProperties.$showModal);
}
