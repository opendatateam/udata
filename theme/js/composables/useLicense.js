import {ref, Ref, unref} from "vue";
import fetchLicenses from "../api/licenses";

/**
 * 
 * @param {string} id 
 * @returns Ref<Object | null>
 */
export default function useLicense(id) {
    id = unref(id);
    /** @type {Ref<Object | null>} */
    const license = ref(null);
    fetchLicenses().then(licenses => {
        const found = licenses.find(license => license.id === id);
        if(found) {
            license.value = found;
        }
    });
    return license;
}
