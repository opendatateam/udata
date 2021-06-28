<template>
  <div class="thread-reply">
    <strong class="fs-sm">{{ $t("Reply to the discussion") }}</strong>
    <form @submit.prevent="submit" class="my-sm">
      <textarea v-model="comment" :placeholder="$t('Comment')" />
      <footer class="row-inline justify-between align-items-center">
        <span class="text-grey-300 fs-sm">
          {{ $t("Reply as") }}
          <Author :author="user" />
        </span>
        <input
          type="submit"
          :value="$t('Submit')"
          class="btn-secondary btn-secondary-green-300"
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
