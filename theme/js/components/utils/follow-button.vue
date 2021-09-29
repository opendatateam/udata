<!--
---
name: Follow
category: Interactions
---

# Follow button

A simple button to follow various entities on the website.
The `following` prop allow to pass the current state (user is already following or user is not following) and makes the component react accordingly on click (follow/unfollow)
`followers` is the number of current followers
The `url` prop is the API URL.
-->

<template>
  <a
    @click.prevent="toggleFollow"
    title=""
    class="unstyled row-inline align-items-center"
    v-show="!readOnlyEnabled"
  >
    <span
      class="btn-secondary btn-secondary-orange-100 p-sm"
      style="line-height: 1"
    >
      <span
        v-html="icon"
        class="magic"
        :class="{ active: animating }"
        :style="{ color: _following ? 'inherit' : 'white' }"
      />
    </span>
    <strong class="text-orange-100 ml-sm"
      >{{ _followers }} {{ $tc("favourites", _followers) }}</strong
    >
  </a>
</template>

<script>
import config from "../../config";
import icon from "svg/actions/star.svg";

export default {
  props: {
    followers: Number,
    url: String,
    following: Boolean,
  },
  created() {
    this.icon = icon;
  },
  data() {
    return {
      loading: false,
      _followers: this.followers || 0,
      _following: this.following,
      animating: false,
      readOnlyEnabled: config.read_only_enabled,
    };
  },
  methods: {
    toggleFollow: function () {
      this.$auth(this.$t("You must be connected to add a favourite."));

      this.loading = true;

      let request;

      if (!this._following) request = this.$api.post(this.url);
      else request = this.$api.delete(this.url);

      request
        .then((resp) => resp.data)
        .then((data) => {
          this._followers = data.followers;
          this._following = !this._following;

          //Trigger sparkles animation
          if (this._following) {
            this.animating = true;
            setTimeout(() => (this.animating = false), 1300);
          }
        })
        .finally(() => (this.loading = false));
    },
  },
};
</script>
