<template>
  <div class="thread-reply">
    <form @submit.prevent="submit">
      <textarea v-model="comment" placeholder="Commentaire" />
      <input type="submit" value="Submit" class="btn-primary" />
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
        this.onSubmit(values).finally(() => {
          vm.loading = false;
          vm.comment = "";
        });
    },
  },
};
</script>
