<template>
  <form @submit.prevent="searchWithoutAutocomplete">
    <div class="fr-search-bar" role="search">
      <label class="fr-label" :for="eventName">
        {{ $t('Search resources') }}
      </label>
      <input
        class="fr-input"
        placeholder="Rechercher"
        type="search"
        :id="eventName"
        v-model="searchValue"
      />
      <button class="fr-btn" :title="$t('Search')" type="submit">
        {{ $t('Search') }}
      </button>
    </div>
  </form>
</template>

<script>
import {reactive, watch, onUnmounted} from 'vue';
import {bus} from "../../plugins/eventbus";
import useDebouncedRef from "../../composables/useDebouncedRef";
import {search_autocomplete_debounce, search_autocomplete_enabled} from "../../config";
export default {
  props: {
    eventName: {
      type: String,
      default: 'search'
    }
  },
  setup(props) {
    const searchValue = useDebouncedRef('', search_autocomplete_debounce);
    const totalResults = reactive(new Map());
    const search = () => bus.emit(props.eventName, searchValue.value);
    if(search_autocomplete_enabled) {
      watch(searchValue, search);
    }
    let timeoutId;
    const searchWithoutAutocomplete = () => {
      timeoutId = setTimeout(() => {
        search();
      }, search_autocomplete_debounce);
    };
    onUnmounted(() => clearTimeout(timeoutId));
    bus.on(props.eventName + ".results.updated", ({type, count}) => {
      totalResults.set(type, count);
    });
    watch(totalResults, results => {
      const total = Array.from(results.values()).reduce((total, resultPerType) => total + resultPerType, 0);
      bus.emit(props.eventName + '.results.total', total);
    });
    return {
      search,
      searchWithoutAutocomplete,
      searchValue,
    }
  }
}
</script>
