import Sortable from 'sortablejs';

export default {
    ready() {
        this.$sortable = Sortable.create(this.$els.sortable, {
            disabled: this.$options.sortable.disabled,
            store: this.$options.sortable.store,
            handle: this.$options.sortable.handle,
            draggable: this.$options.sortable.draggable,
            filter: this.$options.sortable.filter,
            animation: this.$options.sortable.animation || 150,
            group: this.$options.sortable.group,
            ghostClass: this.$options.sortable.ghostClass,

            // dragging started
            onStart: (/**Event*/evt) => {
                this.$emit('sorter:start', evt); // element index within parent
            },

            // dragging ended
            onEnd: (/**Event*/evt) => {
                this.$emit('sorter:end', evt);
                // evt.oldIndex;  // element's old index within parent
                // evt.newIndex;  // element's new index within parent
            },

            // Element is dropped into the list from another list
            onAdd: (/**Event*/evt) => {
                this.$emit('sorter:add', evt);
                // var itemEl = evt.item;  // dragged HTMLElement
                // evt.from;  // previous list
                // + indexes from onEnd
            },

            // Changed sorting within list
            onUpdate: (/**Event*/evt) => {
                // var itemEl = evt.item;  // dragged HTMLElement
                // + indexes from onEnd
                this.$emit('sorter:update', evt);
            },

            // Called by any change to the list (add / update / remove)
            onSort: (/**Event*/evt) => {
                // same properties as onUpdate
                this.$emit('sorter:sort', evt);
            },

            // Element is removed from the list into another list
            onRemove: (/**Event*/evt) => {
                // same properties as onUpdate
                this.$emit('sorter:remove', evt);
            },

            // Attempt to drag a filtered element
            onFilter: (/**Event*/evt) => {
                // var itemEl = evt.item;  // HTMLElement receiving the `mousedown|tapstart` event.
                this.$emit('sorter:filter', evt);
            }
        });
    }
};
