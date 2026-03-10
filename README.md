# rdflib-geosparql
An implementation of the GeoSPARQL standard's functions for use with RDFlib Graphs

## Capabilities

The library implements the following functions:

* GeoSPARQL 1.0 and GeoSPARQL 1.1 Functions using the official namespace geof: http://www.opengis.net/def/function/geosparql/
* Further geospatial functions which have not yet been standardized in GeoSPARQL under the namespace geofe:http://www.opengis.net/def/function/geosparql/ext/

URIs of standardized GeoSPARQL functions will not change.
URIs of non-standardized functions might change in the case that these functions become standardized and assigned a new URI.

 
### Literal Types

rdflib-geosparql supports the following geospatial literal types:

* Well-Known Text Literal (GeoSPARQL 1.0)
* GML Literal (GeoSPARQL 1.0)
* KML Literal (GeoSPARQL 1.1)
* GeoJSON Literal (GeoSPARQL 1.1)
* DGGS Literal (GeoSPARQL 1.1)

The DGGS Literal is able to support a variety of DGGS systems.
rdflib-geosparql only supports a subset of DGGS systems, but support may be expanded in the future








