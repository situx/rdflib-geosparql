# rdflib-geosparql
An implementation of the GeoSPARQL standard's functions for use with RDFlib Graphs

## Capabilities

The library implements the following functions:

* GeoSPARQL 1.0 and GeoSPARQL 1.1 Functions using the official namespace geof: http://www.opengis.net/def/function/geosparql/
* Further geospatial functions which have not yet been standardized in GeoSPARQL under the namespace geofe:http://www.opengis.net/def/function/geosparql/ext/

URIs of standardized GeoSPARQL functions will not change.
URIs of non-standardized functions might change in the case that these functions become standardized and assigned a new URI.

## Jupyter Notebooks as Tutorials

This repository includes the following Jupyter Notebooks which showcase the implemented query functions on the given [testdataset](tests/testdata.ttl).

* [GeoSPARQL 1.0 Functions](GeoSPARQL10.ipynb)
* [GeoSPARQL 1.1 Functions](GeoSPARQL11.ipynb)
* [GeoSPARQL Ext Functions](GeoSPARQLExt.ipynb)

The query functions in these Jupyter Notebooks are almost exclusively operating on WKT Literals.
For a more comprehensive test please refer to the Python test classes in the [tests folder](tests).

While the Jupyter Notebooks are automatically rendered in Github, not all features of the Jupyter Notebooks are available in the GitHub rendering (e.g. Leaflet Map Views).
To make use of these visualizations, please clone the repository and execute the Jupyter Notebook in your preferred Jupyter Notebook environment.
 
### Literal Types

rdflib-geosparql supports the following geospatial literal types:

* DGGS Literal (GeoSPARQL 1.1)
* GML Literal (GeoSPARQL 1.0)
* KML Literal (GeoSPARQL 1.1)
* GeoJSON Literal (GeoSPARQL 1.1)
* GLTF Literal (GeoSPARQL Ext)
* JSONFG Literal (GeoSPARQL Ext)
* PLY Literal (GeoSPARQL Ext)
* Well-Known Text Literal (GeoSPARQL 1.0)

The DGGS Literal is able to support a variety of DGGS systems.
rdflib-geosparql only supports a subset of DGGS systems, but support may be expanded in the future








