import { inject } from 'vue';

export function useToast() {
  return inject('toast');
}
