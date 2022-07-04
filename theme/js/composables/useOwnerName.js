import {ref, Ref, ComputedRef, unref} from 'vue';

/**
 * A resource, dataset, reuse or any other object owned by an organization or a user.
 * @typedef Owned
 * @type {Object}
 * @property {{name: string}} [organization] - The resource, dataset or reuse organization.
 * @property {{first_name: string, last_name: string}} [owner] - The resource, dataset or reuse user.
 */

/**
 *
 * @param {Owned|ComputedRef<Owned>} owned - The resource, dataset or reuse owned by an organization or a user.
 * @return {Ref<string>}
 */
export default function useOwnerName(owned) {
  owned = unref(owned);
  const owner = ref('');
  if(!owned) {
    return owner;
  }
  if(owned.organization) {
    owner.value = owned.organization.name;
  } else if(owned.owner) {
    owner.value = owned.owner.first_name + " " + owned.owner.last_name;
  }
  return owner;
}
