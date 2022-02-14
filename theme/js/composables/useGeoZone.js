import {onMounted, ref} from 'vue';
import {api} from "../plugins/api";

const geoZonePromises = {};

export default function useGeoZone(spatial) {
  const geoZone = ref(null);
    const getGeoZones = async () => {
      const zones = spatial?.zones;
      if (zones) {
        let promises = [];
        for(const zone of zones) {
          if(!geoZonePromises[zone]) {
            geoZonePromises[zone] = api
              .get("spatial/zone/" + zone)
              .then((resp) => resp.data)
              .then((obj) => obj && obj?.properties?.name);
          }
          promises.push(geoZonePromises[zone]);
        }
        geoZone.value = await Promise.all(promises);
      }
    };

    onMounted(getGeoZones);

    return {
      geoZone,
    }
}
