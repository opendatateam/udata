import {api} from "../plugins/api";


let licenses = null;
let licensesRequest = null;

/**
 * 
 * @returns {Promise<Array>}
 */
export default function fetchLicenses() {
  if (licensesRequest) {
    return licensesRequest;
  }
  return licensesRequest = api.get('/datasets/licenses/')
  .then((resp) => resp.data)
  .then((data) => licenses = data);
}
