define(['sortablejs'], function(Sortable) {
    'use strict';

    return {
        ready: function() {
            this.$sortable = Sortable.create(this.$els.sortable, {
                // sort: this.$options.sortable.sort || true,
                disabled: this.$options.sortable.disabled,
                store: this.$options.sortable.store,
                handle: this.$options.sortable.handle,
                draggable: this.$options.sortable.draggable,
                filter: this.$options.sortable.filter,
                animation: this.$options.sortable.animation || 150,
                group: this.$options.sortable.group,
                ghostClass: this.$options.sortable.ghostClass,
                // scroll: this.$options.sortable.scroll,
                // scrollSensitivity: this.$options.sortable.scrollSensitivity,
                // scrollSpeed: this.$options.sortable.scrollSpeed,
                // setData: function (dataTransfer, dragEl) {
                //     this.$emit('sorter:data', dataTransfer, dragEl);
                // }.bind(this),

                // dragging started
                onStart: function (/**Event*/evt) {
                    this.$emit('sorter:start', evt); // element index within parent
                }.bind(this),

                // dragging ended
                onEnd: function (/**Event*/evt) {
                    this.$emit('sorter:end', evt);
                    // evt.oldIndex;  // element's old index within parent
                    // evt.newIndex;  // element's new index within parent
                }.bind(this),

                // Element is dropped into the list from another list
                onAdd: function (/**Event*/evt) {
                    this.$emit('sorter:add', evt);
                    // var itemEl = evt.item;  // dragged HTMLElement
                    // evt.from;  // previous list
                    // + indexes from onEnd
                }.bind(this),

                // Changed sorting within list
                onUpdate: function (/**Event*/evt) {
                    // var itemEl = evt.item;  // dragged HTMLElement
                    // + indexes from onEnd
                    this.$emit('sorter:update', evt);
                }.bind(this),

                // Called by any change to the list (add / update / remove)
                onSort: function (/**Event*/evt) {
                    // same properties as onUpdate
                    this.$emit('sorter:sort', evt);
                }.bind(this),

                // Element is removed from the list into another list
                onRemove: function (/**Event*/evt) {
                    // same properties as onUpdate
                    this.$emit('sorter:remove', evt);
                }.bind(this),

                // Attempt to drag a filtered element
                onFilter: function (/**Event*/evt) {
                    // var itemEl = evt.item;  // HTMLElement receiving the `mousedown|tapstart` event.
                    this.$emit('sorter:filter', evt);
                }.bind(this)
            });
        },
    };
});
