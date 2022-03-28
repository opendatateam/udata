/**
 * @typedef keyCodesModel
 * @property {number} TAB
 * @property {number} ESCAPE
 * @property {number} END
 * @property {number} HOME
 * @property {number} LEFT
 * @property {number} UP
 * @property {number} RIGHT
 * @property {number} DOWN
 */

/**
 * @type keyCodesModel
 */
const KEYCODES = window.dsfr.core.KeyCodes;

export default function useKeyCodes() {
  return {
    KEYCODES: {
      ...KEYCODES,
      ALT: 18,
      CTRL: 17,
      SHIFT: 16,
      CAPS_LOCK: 20,
    },
  }
}
