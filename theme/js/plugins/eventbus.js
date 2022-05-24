/*
---
name: Events
category: 6 - Technical
---

# Events

Events are dispatched in different parts of the app to allow component interactions or even interaction between multiple vue instances.

Our emitter is available in instance as `$bus` or directly by importing `eventbus.js` file.
It allows us to listen to all events or to a single event type.

```listen.js
import {bus} from "../../plugins/eventbus";
bus.on("*", (type, e) => console.log(type, e));
bus.on("someType", (e) => console.log(e));

// or, inside a component
this.$bus.on("*", (type, e) => console.log(type, e));
this.$bus.on("someType", (e) => console.log(e));
```

## Dispatch event

A new event can be dispatched with the dispatch method.

```listen.js
import {bus} from "../../plugins/eventbus";
bus.dispatch("someType", "someValue");

// or, inside a component
this.$bus.dispatch("someType", "someValue");
```

## Event list

The following events are used :

Type | Parameter | Emitted
--- | --- | ---
`discussions.startThread` | none | when user want to start a new discussion thread
`suggest.startSearch` | none | when user want to start a new suggest search
`resources.search` | search input value | when a new resource search is submitted
`resources.search.results.updated` | {type: the resource type <br/> count : the number of resources for this type} | when search results are received from API
`resources.search.results.total` | total of search results | when search count are received from event `resources.search.results.updated`

*/

import mitt, {Emitter as EmitterMitt} from "mitt";

export const DISCUSSIONS_START_THREAD = "discussions.startThread";
export const RESOURCES_SEARCH = "resources.search";
export const RESOURCES_SEARCH_RESULTS_UPDATED = "resources.search.results.updated";
export const RESOURCES_SEARCH_RESULTS_TOTAL = "resources.search.results.total";


/**
 * @typedef {DISCUSSIONS_START_THREAD | RESOURCES_SEARCH | RESOURCES_SEARCH_RESULTS_UPDATED | RESOURCES_SEARCH_RESULTS_TOTAL} UdataEventType
 */

/**
 * @typedef {Record<UdataEventType, unknown>} Events
 */

/**
 * @type {EmitterMitt<Events>} Emitter of
 */
export const bus = mitt();

export const install = (app) => {
  app.config.globalProperties.$bus = bus;
};

export default install;
