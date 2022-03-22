/*
---
name: Clipboard
category: 5 - Interactions
---

# Interaction
Copy to clipboard thanks to clipboardjs.com
Just have an element with an `id` ending with `-copy` and use clipboardJS API for endless possibilities !

```clipboard.html
<input id="something-copy" value="Some value" />
<button class="btn" data-clipboard-target="#something-copy">
    Copy !
</button>
```
*/

import ClipboardJS from "clipboard";

export default (() => {
  document.addEventListener("DOMContentLoaded", () => {
    new ClipboardJS('[id$="-copy"]');
  });
})();
