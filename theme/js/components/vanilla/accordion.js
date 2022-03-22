/*
---
name: Accordion
category: 5 - Interactions
---

# Interaction
Because accordion are not only seen in the subway, you can use this tidbit to create collapsible ARIA-compatible accordions.

The button needs to have :
- `.accordion-button` class
- `aria-controls` and `href` set to a valid `#id` on the page
- `aria-label` to explain what the button does if there's not enough text in the button itself (like an icon)
- `aria-expanded` set to either `true` (if the accordion is visible by default) or `false`
-  An optional `.trigger-once` class that will make the button disappear once the content it controls is expanded

The accordion panel needs to have :

- `.accordion-content` class
- `.active` class if the accordion is visible by default
- `aria-labelledby` set to the button's `#id`
- A valid `#id` corresponding to the button's `href`


```accordion.html
<a class="accordion-button" aria-controls="toggle-me" aria-expanded="true" href="#toggle-me">Toggle the thingies</a>
<section class="accordion-content active" aria-labelledby="resource-header" id="toggle-me">Nice collapsible section (visible by default, click the button to hide)</h1>
```
*/

import { easing, tween, styler } from "popmotion";

export default (() => {
  document.addEventListener("DOMContentLoaded", () => {
    const togglers = document.querySelectorAll(".accordion-button");

    //For each toggler button
    togglers.forEach((toggler) => {
      toggler.addEventListener("click", (ev) => {
        ev.preventDefault();

        //Toggling the aria-expanded attribute on the button
        if (ev.target.getAttribute("aria-expanded") === "true")
          ev.target.setAttribute("aria-expanded", "false");
        else ev.target.setAttribute("aria-expanded", "true");

        const target = document.querySelector(ev.target.getAttribute("href"));
        const divStyler = styler(target);

        if (target) {
          target.classList.toggle("active");

          if (target.classList.contains("active")) {
            tween({
              from: { height: 0 },
              to: { height: target.scrollHeight },
              duration: 300,
              ease: easing.anticipate,
            }).start({
              update: divStyler.set,
              complete: () => divStyler.set({ height: "auto" }),
            });
          } else {
            tween({
              from: { height: target.scrollHeight },
              to: { height: 0 },
              duration: 300,
              ease: easing.anticipate,
            }).start(divStyler.set);
          }
        }
      });
    });
  });
})();
