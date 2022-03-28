import { ref, unref, onMounted, onUnmounted } from 'vue'
import useKeyCodes from "./useKeyCodes";

let uid = 0;

export function useCollapse() {
  const {KEYCODES} = useKeyCodes();
  let registration;
  uid += 1;
  const collapseId = `collaspe-${uid}`;
  const expanded = ref(false);

  const show = () => expanded.value = true;

  const hide = () => expanded.value = false;

  const toggle = () => expanded.value = !expanded.value;

  onMounted(() => {
    registration = window.dsfr.register(`#${collapseId}`, window.dsfr.core.Collapse);
    console.log(`#${collapseId} registered as collapse`);
  });

  onUnmounted(() => {
    registration.dispose();
    console.log(`#${collapseId} unregistered as collapse`);
  });

  let registeredEventHandler = null;

  const registerBackgroundEvent = (inputRef, listRef, buttonRef) => {
    const input = unref(inputRef);
    const list = unref(listRef);
    const button = unref(buttonRef);
    registeredEventHandler = onBackgroundPointerUp(input, list, button);
    document.body.addEventListener(
      'pointerup',
      registeredEventHandler,
      true
    );
  }

  const removeBackgroundEvent = () => {
    document.body.addEventListener(
      'pointerup',
      registeredEventHandler,
      true
    );
  }

  const onBackgroundPointerUp = (input, list, button) => (event) => {
    if (
      !input.contains(event.target) &&
      !list.contains(event.target) &&
      !button.contains(event.target)
    ) {
      hide();
    }
  }

  /**
   *
   * @param {KeyboardEvent} key
   */
  const handleKeyPressForCollapse = (key) => {
    switch (key.keyCode) {
      case KEYCODES.ALT:
      case KEYCODES.CTRL:
      case KEYCODES.SHIFT:
      case KEYCODES.CAPS_LOCK:
        break;
      case KEYCODES.ESCAPE:
      case KEYCODES.TAB:
        hide();
        break;
      default:
        show();
    }
  };

  return {
    expanded,
    uid: collapseId,
    show,
    hide,
    toggle,
    registerBackgroundEvent,
    removeBackgroundEvent,
    handleKeyPressForCollapse,
  }
}
