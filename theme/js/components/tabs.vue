<template>
  <div class="tabby">
    Coucou !
    <Slot />
  </div>
</template>

<script>
export default {
  created: () => {
    console.log('Im compiling')
  },
};
</script>
