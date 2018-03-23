const recoUrl = 'https://raw.githubusercontent.com/etalab/datasets_reco/master/reco_json/';
const maxRecos = 2;

function getDatasetId() {
    const selector = '#json_ld';
    const dataset = JSON.parse(document.querySelector(selector).text);
    return dataset && dataset['@id'];
}

function addRecos(recos) {
    window._paq = window._paq || [];

    const recoContainer = document.getElementById('dataset-recommendations-container');
    let recoChildContainer, recoChildEmbed;

    recos.splice(0, maxRecos).forEach((reco, idx) => {
        recoChildContainer = document.createElement('div');

        recoChildContainer.setAttribute('data-track-content', '');
        recoChildContainer.setAttribute('data-content-name', 'dataset recommendations');
        recoChildContainer.setAttribute('data-content-piece', 'reco ' + idx);
        recoChildContainer.setAttribute('data-content-target', 'datasets/' + reco[0]);
        recoChildContainer.setAttribute('data-udata-dataset', reco[0]);

        recoChildContainer.classList.add('recommendation', 'col-xs-12', 'col-md-6');

        recoContainer.appendChild(recoChildContainer);
    });

    window._paq.push(['trackContentImpressionsWithinNode', recoContainer]);
}

function addWidgetScript() {
    const scriptElm = document.createElement('script');
    scriptElm.src = '/static/oembed.js';
    document.body.appendChild(scriptElm);
}

function fetchRecos(datasetId) {
    fetch(recoUrl + datasetId + '.json').then((response) => {
        if(response.ok) {
            return response.json();
        }
    }).then((recos) => {
        recos = recos && recos[datasetId];
        if (recos) {
            addRecos(recos);
            addWidgetScript();
            document.getElementById('dataset-recommendations').style.display = 'block';
        }
    }).catch((err) => {
        console.log('Error while fetching recommendations:', err);
    });
}

global.udataDatasetRecos = {
    load() {
        const datasetId = getDatasetId();
        if (datasetId) {
            fetchRecos(datasetId);
        }
    }
}
