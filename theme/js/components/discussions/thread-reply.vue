<template>
  <div class="thread-reply">
    <div class="fr-grid-row fr-grid-row--middle fr-mb-3v">
      <h4 class="fr-col fr-text--bold fr-mb-0">{{ $t("Reply to the discussion") }}</h4>
      <div class="fr-col-auto">
        <button class="fr-link--close fr-link text-grey-500 fr-mr-0" @click="$emit('close')">
          {{$t('Close')}}
        </button>
      </div>
    </div>
    <form class="form fr-p-0" @submit.prevent="submit">
      <i18n-t
        keypath="Fields preceded by a star ({markup}) are required."
        tag="p"
        class="fr-mt-0 fr-mb-1w fr-text--xs"
        scope="global"
      >
        <template #markup>
          <span class="required-field-star">*</span>
        </template>
      </i18n-t>
      <div class="fr-input-group">
        <label class="fr-label required" for="textarea">
          {{$t('Comment')}}
        </label>
        <textarea v-model="comment" required class="fr-input" id="textarea"></textarea>
      </div>
      <footer class="fr-grid-row justify-between fr-grid-row--middle">
        <span class="text-mention-grey fr-text--sm fr-mb-0">
          {{ $t("Reply as") }}
          <Author :author="user" />
        </span>
        <input
          type="submit"
          :value="$t('Submit')"
          class="fr-btn fr-btn--secondary fr-btn--secondary-grey-500"
        />
      </footer>
    </form>
  </div>
</template>

<script>
import config from "../../config";
import Author from "./author.vue";

const log = console.log;

export default {
  components: {
    Author,
  },
  emits: ['close'],
  data() {
    return {
      loading: false,
      comment: "",
      user: config.user,
    };
  },
  props: {
    subjectId: String,
    subjectClass: String,
    onSubmit: Function,
  },
  methods: {
    submit() {
      const vm = this;
      this.loading = true;

      const values = {
        comment: this.comment,
        subject: {
          id: this.subjectId,
          class: this.subjectClass,
        },
      };

      if (this.onSubmit)
        this.onSubmit(values)
          .catch((err) => {
            vm.$toast.error(vm.$t("Error sending response"));
          })
          .finally(() => {
            vm.loading = false;
            vm.comment = "";
          });
    },
  },
};
</script>
