<!--
---
name: RequestMembership
category: Interactions
---

# Request Membership

A simple request membership prompt.
-->

<template>
  <button
    @click.prevent="JoinOrga"
    class="nav-link nav-link--no-icon text-decoration-none fr-link fr-link--icon-left fr-fi-arrow-right-s-line"
  >
    <span class="text-decoration-underline">{{ $t('Ask to join the organization as a producer') }}</span>
  </button>
</template>

<script>

export default {
  props: {
    orga: String,
  },
data() {
    return {
        comment: '',
    };
},
  methods: {
    JoinOrga: function () {

      this.$auth(this.$t("You must be connected to join an organization"));

      this.comment = prompt(this.$t('You can add some details here for your membership request'));

      this.$api.post("organizations/" + this.orga + "/membership/", {comment: this.comment})
          .then(data => {
            alert(this.$t('A request has been sent to the administrators'));
            window.location.reload();
        })
        .catch(error => {
            alert(this.$t('Error while requesting membership'));
            log.error(error);
        });
      }
  }
};
</script>
