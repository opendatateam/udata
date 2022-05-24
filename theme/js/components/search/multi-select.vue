<!--
---
name:  Multi-select
category: Search
---

# Multi-select

A pretty simple component that looks like a `<select>` but with autocomplete features.

Options can be :
- A list from an API that will be fetched once
- A suggest-style API that will be fetched on each character typed
- A combination of both : a static list on load that is replaced when the user types something

* Initial values can be provided from props (can be used to pre-fill the select with values from the URL)

## Usage

Simply provide the necessary props for your case.

Urls:
- `suggestUrl`(optional): The URL that will be called when the user performs a search within the select.
  If not provided, suggest mode will be disabled and typing in the select will only filter the existing options.
  If provided, you can add a `minimumCharacterBeforeSuggest` props
- `listUrl`(optional): The URL that will be called to populate the select options on mount.
  If not provided, the select will start empty and will fill with options when the user starts typing some text.
- `entityUrl`(optional): The URL that will be called to fetch labels for options provided before the component mounts.

Texts:
- `placeholder`: Select placeholder, always shown
- `searchPlaceholder`: Search input placeholder
- `emptyPlaceholder`: Options placeholder when there is no search results
- `explanation`: Title attribute added to select label

Options:
- `initialOptions`: Initial list of options
- `values`: Initial values if the select needs to be pre-filled. Can be a String (single value) or an Array of values.
  Labels will be fetched from entityUrl, or from the options list if listUrl is provided, or the value will be used as label.

Configuration:
- `minimumCharacterBeforeSuggest`: wait for this count of character before calling suggest

Callback:
- `onChange`: Function that will be called on each value select/deselect action.

```
-->

<template>
  <div class="multiselect w-100" ref="container" :data-selected="!!selected">
    <label :for="id" :title="explanation">{{placeholder}} <span v-if="explanation" class="fr-fi-information-line" aria-hidden="true"></span></label>
    <select
      class="multiselect__input"
      :id="id"
      ref="select"
      v-model="selected"
    >
      <option
        v-for="option in displayedOptions"
        :key="option.value"
        :value="option.value"
        :data-image="option.image"
      >
        {{option.label}}
      </option>
    </select>
  </div>
</template>

<script>
import {defineComponent, ref, Ref, computed, onMounted, onUpdated, reactive, PropType, unref, watch} from "vue";
import Select from "@conciergerie.dev/select-a11y/dist/module";
import {useI18n} from 'vue-i18n';
import axios from "axios";
import { CancelTokenSource } from "axios";
import {api, generateCancelToken} from "../../plugins/api";
import useUid from "../../composables/useUid";
import { useToast } from "../../composables/useToast";

/**
 * @typedef {Object} Option
 * @property {string} label - Label (display) of the option
 * @property {string} value - Value (id) of the option
 * @property {string} [image] - Image (optional) to show
 */

export default defineComponent({
  props: {
    suggestUrl: String,
    listUrl: String,
    entityUrl: String,
    /** @type {PropType<Promise<Option[]>>} */
    initialOptions: Promise,
    values: [Array, String],
    onChange: {
      type: Function,
      required: true,
    },
    placeholder: {
      type: String,
      required: true,
    },
    explanation: {
      type: String,
      default: '',
    },
    searchPlaceholder: {
      type: String,
      required: true,
    },
    emptyPlaceholder: {
      type: String,
    },
    allOption: {
      type: String,
      default: '',
    },
    minimumCharacterBeforeSuggest: {
      type: Number,
      default: 1,
    }
  },
  setup(props) {
    const { t } = useI18n();
    const toast = useToast();
    const { id } = useUid('multiselect');

    /** 
    * Select template Ref
    * @type {Ref<HTMLSelectElement|null>}
    */
    const select = ref(null);

    /**
     * Container Template Ref
     * @type {Ref<HTMLElement|null>}
     */
    const container = ref(null);

    /**
     * Popup offset if required
     */
    const offset = ref(0);

    /**
     * Mimimum popup width
     */
    const minWidth = 350;

    /**
     * Maximum options count
     */
    const maxOptionsCount = 200;

    /**
     * Current options
     * @type {Ref<Option[]>}
     */
    const options = ref([]);

    /**
     * Displayed Options limited to {@link maxOptionsCount}
     */
    const displayedOptions = computed(() => options.value.slice(0, maxOptionsCount));

    /**
     * Current selected value(s)
     * @type {Ref<string | null>}
     */
    const selected = ref(null);

    const defaultValue = '';

    /**
     * Current request if any to be cancelled if a new one comes
     * @type {Ref<CancelTokenSource | null>}
     */
    const currentRequest = ref(null);

    /**
     * Select instance
     * @type {Select | null}
     */
    const selectA11y = ref(null);

    const noResultAfterSearch = computed(() => props.emptyPlaceholder || t("No results found."));

    const texts = reactive({
      help: t('Use tab (or arrow down) to move between suggestions'),
      placeholder: props.searchPlaceholder,
      noResult: noResultAfterSearch.value,
      results: t('{x} available suggestion'),
      deleteItem: t('Delete {t}'),
      delete: t('Delete'),
    });

    /**
     * Get initial set of options from API or an empty array
     * @returns {Promise<Option[]>}
     */
    const getInitialOptions = async () => {
      if(props.initialOptions) return props.initialOptions;
      if (!props.listUrl) return [];

      /**
       * @type {import("axios").AxiosResponse<{data: Array}|Array>}
       */
      const resp = await api.get(props.listUrl);
      let data = resp.data;
      if(!Array.isArray(data)) {
        data = data.data;
      }
      return mapToOption(data);
    };

    /**
     * Map an array of all different objects received from API to an array of {@link Option}
     * @param {Array} data
     * @returns {Array<Option>}
     **/
    const mapToOption = (data) => data.map((obj) => ({
      label: obj.name ?? obj.title ?? obj.text ?? obj?.properties?.name ?? obj.label ?? obj,
      value: obj.id ?? obj.text ?? obj.value ?? obj,
      image: obj.logo_thumbnail ?? obj.logo ?? obj.image_url ?? obj.image,
    }));

    /**
     * Get options from suggest API
     * It uses list API if no query is provided
     * Fallback to an empty array without props.listUrl
     * @param {string} q 
     * @returns {Promise<Array<Option>>}
     */
    const suggest = (q) => {
      if(q.length < props.minimumCharacterBeforeSuggest || !props.suggestUrl) {
        return getInitialOptions();
      }
      if (currentRequest.value) {
        currentRequest.value.cancel();
      }

      currentRequest.value = generateCancelToken();
      return api
        .get(props.suggestUrl, {
          params: { q, size: maxOptionsCount },
          cancelToken: currentRequest.value.token,
        })
        .then((resp) => {
          /** @type Array */
          const suggestions = resp.data;
          return suggestions;
        })
        .catch((error) => {
          if (!axios.isCancel(error)) {
            toast.error(t("Error getting {type}.", {type: props.placeholder}));
          }
          return [];
        });
    };

    const suggestAndMapToOption = (q = '') => suggest(q).then(addAllOptionAndMapToOption);

    /**
     * Get options from suggest API
     * It uses list API if no query is provided
     * Fallback to an empty array without query and props.listUrl
     * @param {Array} suggestions 
     * @returns {Array<Option>}
     */
    const addAllOptionAndMapToOption = (suggestions) => {
      if(props.allOption) {
        suggestions.unshift({name: props.allOption, id: ''});
      }
      return mapToOption(suggestions);
    }

    /**
     * Set options from DOM processing
     * @param {Option[] | void} values
     * @returns {Option[] | void}
     */
    const setOptions = (values) => {
      if(values) {
        options.value = values;
      }
      return values;
    };

    /**
     * Normalize provided values to array
     * @param {string | Array | undefined} values 
     * @returns {Ref<string>}
     */
    const normalizeValues = (values) => {
      /**
       * Selected value
       * @type {Ref<string>}
       */
      const selected = ref('');
      if (typeof values === "string") {
        selected.value = values;
      } else if (Array.isArray(values)) {
        selected.value = values[0];
      }
      return selected;
    }

    /**
     * Fill selected array with initial props.values.
     * It tries to augment the values with data from props.entityUrl or options.
     */
    const fillSelectedFromValues = () => {
      let selectedPromise = null;
      let value = unref(normalizeValues(props.values));
      if (value && props.entityUrl) {
          selectedPromise = api
            .get(props.entityUrl + value)
            .then((resp) => resp.data)
            .then((data) => mapToOption([data]))
            .then((entities) => entities[0]?.label ?? value)
            .then((label) => {
              const newOption = options.value.every(option => option.value !== value);
              if(newOption) {
                options.value.push({label, value});
              }
            })
            .then(() => value);
        } else {
          let option = options.value.find((opt) => opt.value === value);
          if (!option) {
            option = {label: value, value};
            options.value.push(option);
          }
          selectedPromise = Promise.resolve(option.value);
        }
      return selectedPromise
        .then(value => selected.value = value)
        .then(value => value ? value : selected.value = defaultValue);
    }

    /**
     * Register event listener to trigger on change on select change event
     */
    const registerTriggerOnChange = () => {
      if(select.value) {
        props.onChange(select.value.value);
      }
    };

    const updateStylesAndEvents = () => {
      updatePopupStyle();
      updateSelectStyle();
      registerSelectEvents();
    }

    const updatePopupStyle = () => {
      if(!container.value) {
        return;
      }
      let rect = container.value.getBoundingClientRect();
      let popupWidth = minWidth;
      if(window.innerWidth < popupWidth) {
        popupWidth = Math.min(minWidth, rect.width);
      }
      let availableSpace = window.innerWidth - rect.x;
      let popupMustMove = availableSpace < popupWidth;
      offset.value = popupMustMove ? popupWidth - rect.width : 0;
      const styles = container.value.style;
      styles.setProperty('--offset-select-a11y__overlay', `-${offset.value}px`);
      styles.setProperty('--min-width-select-a11y__overlay', `${popupWidth}px`);
    }

    const updateSelectStyle = () => {
      if(!container.value) {
        return;
      }
      const selectA11y = container.value.querySelector('.select-a11y');
      if(selectA11y) {
        selectA11y.classList.add("fr-select");
      }
    };
    
    const registerSelectEvents = () => {
      if(!container.value) {
        return;
      }
      if(select.value) {
        select.value.removeEventListener('change', registerTriggerOnChange);
        select.value.addEventListener('change', registerTriggerOnChange);
      }
    };

    const makeSelect = () => {
      const options = {
        text: texts,
        clearable: true,
      };
      if(props.suggestUrl) {
        options.fillSuggestions = suggestAndMapToOption;
      }
      try {
        selectA11y.value = new Select(select.value, options);
        updateStylesAndEvents();
      } catch (e) {
        console.log(e);
      }
    };

    watch(() => props.values, () => {
      let value = unref(normalizeValues(props.values));
      selectA11y.value.selectOption(value);
    });
    
    const fillOptionsAndValues = suggestAndMapToOption()
    .then(setOptions)
    .then(fillSelectedFromValues);

    onMounted(() => fillOptionsAndValues.then(makeSelect));
    onUpdated(updateStylesAndEvents);
    return {
      id,
      displayedOptions,
      selected,
      select,
      container,
      offset,
    }
  }
});
</script>

<style scoped>
.multiselect :deep(.select-a11y__overlay) {
  left: var(--offset-select-a11y__overlay);
  min-width: var(--min-width-select-a11y__overlay);
}
</style>
