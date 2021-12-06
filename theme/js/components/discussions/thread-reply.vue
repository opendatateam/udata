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
    <form @submit.prevent="submit">
      <div class="fr-input-group">
        <label class="fr-label" for="textarea">
          {{$t('Comment')}}
        </label>
        <textarea v-model="comment" class="fr-input" id="textarea"></textarea>
      </div>
      <footer class="fr-grid-row justify-between fr-grid-row--middle">
        <span class="text-g600 fr-text--sm fr-mb-0">
          {{ $t("Reply as") }}
          <Author :author="user" />
        </span>
        <input
          type="submit"
          :value="$t('Submit')"
          class="btn-secondary btn-secondary-grey-500 fr-btn fr-btn--secondary"
        />
      </footer>
    </form>
  </div>
</template>

<script>
import config from "../../config";
import Author from "./author";

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
