<template>
  <div class="thread-reply">
    <strong class="fs-sm">{{ $t("@@Répondre à la discussion") }}</strong>
    <form @submit.prevent="submit" class="my-sm">
      <textarea v-model="comment" :placeholder="$t('@@Commentaire')" />
      <footer class="row-inline justify-between align-items-center">
        <span class="text-grey-300 fs-sm"
          >{{ $t("@@Répondre en tant que") }}
          <strong>{{ user.first_name + " " + user.last_name }}</strong></span
        >
        <input
          type="submit"
          :value="$t('@@Valider')"
          class="btn-secondary btn-secondary-green-300"
        />
      </footer>
    </form>
  </div>
</template>

<script>
import config from "../../config";

const log = console.log;

export default {
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
            vm.$toast.error(vm.$t("@@Erreur lors de l'envoi de la réponse"));
          })
          .finally(() => {
            vm.loading = false;
            vm.comment = "";
          });
    },
  },
};
</script>
