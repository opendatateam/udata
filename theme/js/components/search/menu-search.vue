<!--
---
name: Menu Search
category: Search
---

# Menu Search

It's an input working like a [combobox](https://www.w3.org/TR/wai-aria-practices/#combobox)
 and based on a [WAI-ARIA Authoring Practices 1.2 example](https://www.w3.org/TR/wai-aria-practices/examples/combobox/combobox-autocomplete-list.html).
-->

<template>
  <div
    class="fr-col fr-grid-row"
  >
    <input
      class="fr-input fr-col"
      :placeholder="$t('Search')"
      type="search"
      ref="input"
      autocomplete="off"
      role="combobox"
      aria-autocomplete="list"
      :aria-controls="uid"
      :aria-expanded="expanded"
      id="search-input"
      data-cy="search-input"
      :aria-activedescendant="selected"
      name="q"
      v-model="q"
      @click.stop.capture="showAndSelectIfQuery"
      @keydown="handleKeyDown"
      @keypress.enter.prevent="searchSelectedOption"
      @blur="handleFocusOut"
    />
    <button
      type="button"
      ref="button"
      class="fr-btn"
      :title="$t('Search')"
      tabindex="-1"
      :aria-controls="uid"
      :aria-expanded="expanded"
      @click.prevent.stop.capture="showAndFocus"
    >
      {{  $t('Search') }}
    </button>
    <div
      class="fr-menu fr-collapse autocomplete"
      :id="uid"
      ref="list"
      role="listbox"
      aria-labelledby="search-label"
      @mousedown.prevent
    >
      <ul class="fr-menu__list" role="listbox">
        <li
          v-for="option in options"
          :key="option.id"
          :id="option.id"
          role="option"
          :aria-selected="isSelected(option.id)"
        >
          <MenuSearchOption :icon="option.icon" :query="q" :type="option.type" :link="option.link"/>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import {ref, defineComponent,reactive, onMounted, onUnmounted} from "vue";
import { useI18n } from 'vue-i18n'
import { useCollapse } from "../../composables/useCollapse";
import MenuSearchOption from "./menu-search-option.vue";
import datasetIcon from "bundle-text:svg/search/dataset.svg";
import reuseIcon from "bundle-text:svg/search/reuse.svg";
import organizationIcon from "bundle-text:svg/search/organization.svg";
import useSearchUrl from "../../composables/useSearchUrl";
import useActiveDescendant from "../../composables/useActiveDescendant";

export default defineComponent({
  components: {MenuSearchOption},
  setup() {
    const {t} = useI18n();
    const {handleKeyPressForCollapse, expanded, uid, show, hide, registerBackgroundEvent, removeBackgroundEvent} = useCollapse();
    const q = ref('');
    const {datasetUrl, reuseUrl, organizationUrl} = useSearchUrl(q);
    /**
     * @typedef MenuOption
     * @property {string} id
     * @property {string} icon
     * @property {string} type
     * @property {string} link
     */

    /**
     * @type {MenuOption[]}
     */
    const options = reactive([
      {
        id: "dataset-option",
        icon: datasetIcon,
        type: t('datasets'),
        link: datasetUrl,
      },
      {
        id: "reuse-option",
        icon: reuseIcon,
        type: t('reuses'),
        link: reuseUrl,
      },
      {
        id: "organization-option",
        icon: organizationIcon,
        type: t('organizations'),
        link: organizationUrl,
      },
    ]);
    const {handleKeyPressForActiveDescendant, select, selected, selectedOption, isSelected, focusOut, NOT_MOVED_YET, ALREADY_MOVED_DOWN} = useActiveDescendant(options);

    const input = ref(null);
    const button = ref(null);
    const list = ref(null);

    onMounted(() => registerBackgroundEvent(input, list, button));
    onUnmounted(() => removeBackgroundEvent());

    const showAndFocus = () => {
      if(!expanded.value) {
        input.value.focus();
        showAndSelectIfQuery();
      } else {
        searchSelectedOption();
      }
    }

    const showAndSelectIfQuery = () => {
      if(q.value) {
        show();
        select(selected.value);
      }
    }

    const handleKeyDown = (e) => {
      showAndSelectIfQuery();
      let moved = NOT_MOVED_YET;
      if(!expanded.value) {
        moved = ALREADY_MOVED_DOWN;
      }
      handleKeyPressForCollapse(e);
      handleKeyPressForActiveDescendant(e, moved);
    }

    const handleFocusOut = () => {
      focusOut();
      hide();
    };

    const searchSelectedOption = () => {
      if(selectedOption.value) {
        window.location.href = selectedOption.value.link;
      }
    }

    return {
      options,
      button,
      input,
      list,
      expanded,
      selected,
      isSelected,
      uid,
      q,
      showAndFocus,
      handleFocusOut,
      showAndSelectIfQuery,
      handleKeyDown,
      searchSelectedOption,
    }
  },
});
</script>
