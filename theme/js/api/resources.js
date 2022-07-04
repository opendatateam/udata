import {api, apiv2} from "../plugins/api";

/**
 * @typedef {import("../composables/useOwnerName").Owned} ResourceModel
 * @property {Object} created_at
 * @property {Object} description
 * @property {Object} extras
 * @property {number} filesize
 * @property {string} filetype
 * @property {string} format
 * @property {string} last_modified
 * @property {string} preview_url
 * @property {string} published
 * @property {Object} schema
 * @property {string} url
 */

/**
 * @param {string} datasetId
 * @param {string} type
 * @param {number} page
 * @param {number} pageSize
 * @param {string} search
 * @return Promise<Array<ResourceModel>>
 */
export const fetchDatasetResources = (datasetId, type, page, pageSize, search) => {
  return apiv2
    .get("/datasets/" + datasetId + "/resources/", {
      params: {
        page,
        type: type,
        page_size: pageSize,
        q: search,
      },
    })
    .then((resp) => resp.data);
}

/**
 * @param {string} datasetId
 * @param {number} page
 * @param {number} pageSize
 * @return Promise<Array<ResourceModel>>
 */
export const fetchDatasetCommunityResources = (datasetId, page, pageSize) => {
  return api
    .get("datasets/community_resources/", {
      params: {
        page,
        dataset: datasetId,
        page_size: pageSize,
      },
    })
    .then((resp) => resp.data)
}
