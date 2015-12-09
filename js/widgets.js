function checkStatus(response) {
  if (response.status >= 200 && response.status < 300) {
    return response;
  } else {
    const error = new Error(response.statusText);
    error.response = response;
    throw error;
  }
}
// Warning: using `Array.from` adds 700 lines once converted through Babel.
[].slice.call(document.querySelectorAll('[data-udata-dataset-id]')).forEach((el) => {
    const datasetId = el.getAttribute('data-udata-dataset-id');
    const oEmbedObjectURL = window.encodeURIComponent(
        `${window.udataURL}/api/1/datasets/${datasetId}/`);
    const url = `${window.udataURL}/api/1/oembed/?url=${oEmbedObjectURL}`;
    fetch(url)
    .then(checkStatus)
    .then((response) => {
        return response.json();
    })
    .then((j) => {
        el.innerHTML = j.html;
    })
    .catch((error) => {
        console.error(error);
    })
})
