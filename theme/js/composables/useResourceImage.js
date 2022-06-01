import code from 'bundle-text:svg/resources/code.svg';
import archive from 'bundle-text:svg/resources/archive.svg';
import documentation from 'bundle-text:svg/resources/documentation.svg';
import file from 'bundle-text:svg/resources/file.svg';
import link from 'bundle-text:svg/resources/link.svg';
import table from 'bundle-text:svg/resources/table.svg';
/***
 *
 * @param {import("../api/resources").ResourceModel} resource
 */
export default function useResourceImage(resource) {
  switch (resource.format?.trim()?.toLowerCase()) {
    case 'txt':
    case 'pdf':
    case 'rtf':
    case 'odt':
    case 'doc':
    case 'docx':
    case 'epub':
      return documentation;
    case 'json':
    case 'sql':
    case 'xml':
    case 'xsd':
    case 'shp':
    case 'kml':
    case 'kmz':
    case 'gpx':
    case 'shx':
    case 'ovr':
    case 'geojson':
    case 'gpkg':
    case 'grib2':
    case 'dbf':
    case 'prj':
    case 'sqlite':
    case 'db':
    case 'sbn':
    case 'sbx':
    case 'cpg':
    case 'lyr':
    case 'owl':
    case 'dxf':
    case 'ics':
    case 'rdf':
    case 'ttl':
    case 'n3':
      return code;
    case 'tar':
    case 'gz':
    case 'tgz':
    case 'rar':
    case 'zip':
     case '7z':
     case 'xz':
     case 'bz2':
      return archive;
    case 'url':
      return link;
    case 'csv':
    case 'ods':
    case 'xls':
    case 'xlsx':
      return table;
    default:
      return file;
  }
}
