import json
import os
from io import BytesIO, TextIOWrapper
import math
from typing import Any

import fastkml.geometry
import h3
import collections
import yaml
import shapelysmooth
import pygeohash
import pygml
import shapely
import trimesh
from fastkml import kml
from lxml import etree
from openlocationcode import openlocationcode
from pint import UnitRegistry
from pygml.v32 import encode_v32
from pyproj import CRS, Transformer
from rdflib import Literal, XSD, Graph, URIRef, term
from rdflib.plugins.sparql.operators import register_custom_function


GEOF = "http://www.opengis.net/def/function/geosparql/"
GEOFEXT = "http://www.opengis.net/def/function/geosparql/ext/"
GEOFPREFIX = "geof:"
GEOFEXTPREFIX = "geofext:"
GEO = "http://www.opengis.net/ont/geosparql#"
CRS84URI = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"

WKTLiteral = "http://www.opengis.net/ont/geosparql#wktLiteral"
GMLLiteral = "http://www.opengis.net/ont/geosparql#gmlLiteral"
KMLLiteral = "http://www.opengis.net/ont/geosparql#kmlLiteral"
DGGSLiteral = "http://www.opengis.net/ont/geosparql#dggsLiteral"
JSONFGLiteral = "http://www.opengis.net/ont/geosparql#jsonfgLiteral"
GEOJSONLiteral = "http://www.opengis.net/ont/geosparql#geoJSONLiteral"
GEOCODELiteral="http://www.opengis.net/ont/geosparql#geocodeLiteral"
GEOYAMLLiteral = "http://www.opengis.net/ont/geosparql#geoYAMLLiteral"
PLYLiteral = "http://www.opengis.net/ont/geosparql#plyLiteral"
OBJLiteral = "http://www.opengis.net/ont/geosparql#objLiteral"
GLTFLiteral = "http://www.opengis.net/ont/geosparql#gltfLiteral"
SVGLiteral = "http://www.opengis.net/ont/geosparql#svgLiteral"
WKBLiteral = "http://www.opengis.net/ont/geosparql#wkbLiteral"
XYZLiteral = "http://www.opengis.net/ont/geosparql#xyzLiteral"


def merge_dicts(*dict_args):
    """
    Given any number of dictionaries, shallow copy and merge into a new dict,
    precedence goes to key-value pairs in latter dictionaries.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

## Transformation functions for SRS, geocodes and DGGS systems
class Transformers:

    #The geocodes supported in this implementation identified by URI
    supported_geocodes = {"http://opengis.net/ont/geocode/GeoURI",
                          "http://opengis.net/ont/geocode/OpenLocationCode",
                          "http://opengis.net/ont/geocode/GeoHash-36",
                          "http://opengis.net/ont/geocode/GeoHash"
                          }

    #The DGGS supported in this implementation identified by URIs
    supported_dggs = {"https://h3geo.org/res/{RESOLUTION}"}

    ## Normalizes a list of geometry tuples to a common SRS.
    #  @param geoms the list of geometry tuples
    #  @param tosrs the target SRS if defined. If none, the SRS of the first geometry is used as the target
    #  @returns A list of transformed geometry tuples
    @staticmethod
    def normalizeGeoms(geoms, tosrs=None):
        geomsnew = []
        if tosrs is None:
            tosrs = geoms[0][1]
        for geom in geoms:
            geomsnew.append((Transformers.transformToSRS(geom[0], geom[1], str(tosrs)), tosrs))
        return geomsnew

    ## Transforms a given geometry to a supported SRS representation.
    #  @param geom The geometry literal
    #  @param fromsrs An identifier of the SRS to transform from (EPSG Code, SRSIRI, Integer)
    #  @param tosrs An identifier of the SRS to transform to (EPSG Code, SRSIRI, Integer)
    #  @returns The transformed geometry in the target SRS
    @staticmethod
    def transformToSRS(geom, fromsrs, tosrs):
        if fromsrs == tosrs:
            return geom
        transformer = Transformer.from_crs(str(fromsrs), str(tosrs))
        res = shapely.transform(geom, transformer.transform, interleaved=False)
        try:
            shapely.set_srid(res, tosrs)
        except:
            pass
        return res

    ## Transforms a given geometry to a supported GeoCode representation.
    #  @param geom The geometry literal
    #  @param geocodeuri The URI identifying the geocode
    #  @returns A string representation which can form the value of a geo:geocodeLiteral
    @staticmethod
    def transformToGeocode(geom, geocodeuri):
        geocodeuri = str(geocodeuri)
        if geocodeuri not in Transformers.supported_geocodes:
            raise ValueError(
                "The Geocode with the given URI " + str(geocodeuri) + " is not supported! Supported geocodes: " + str(
                    Transformers.supported_geocodes))
        thecode = ""
        if geocodeuri == "http://opengis.net/ont/geocode/GeoURI":
            thecode = "geo:" + str(geom.centroid.x) + "," + str(geom.centroid.y) + (
                "," + str(geom.centroid.z) if geom.has_z else "")
        elif geocodeuri == "http://opengis.net/ont/geocode/OpenLocationCode":
            thecode = openlocationcode.encode(geom.centroid.x, geom.centroid.y)
        elif geocodeuri == "http://opengis.net/ont/geocode/GeoHash-36" or geocodeuri == "http://opengis.net/ont/geocode/GeoHash":
            thecode = pygeohash.encode(latitude=geom.x, longitude=geom.y)
        return "<" + str(geocodeuri) + "> " + str(thecode)

    ## Transforms a given geometry to a supported DGGS representation.
    #  @param geom The geometry literal
    #  @param dggsuri The URI identifying the DGGS
    #  @param resolution The resolution of the DGGS to target
    #  @returns A string representation which can form the value of a geo:dggsLiteral
    @staticmethod
    def transformToDGGS(geom, dggsuri,resolution=7):
        thevalue=""
        for dggsuri in Transformers.supported_dggs:
            if dggsuri.startswith("https://h3geo.org/res/"):
                thevalue=h3.geo_to_cells(geom,resolution)
        if thevalue!="":
            return "<" + str(dggsuri).replace("{RESOLUTION}",str(resolution)) + "> CELLLIST(" + str(thevalue).replace("[","").replace("]","")+")"
        raise ValueError(
            "The DGGS with the given URI " + str(dggsuri) + " is not supported! Supported DGGS: " + str(
                Transformers.supported_dggs))

    ## Transforms a given geocode representation to a geometry.
    #  @param geocodestr The geocode to transform
    #  @param geocodeuri The URI identifying the geocode. May also be extracted from the geocode string itself if present
    #  @returns The converted geometry
    @staticmethod
    def geocodeToGeom(geocodestr,geocodeuri=""):
        if "<" in geocodestr and ">" in geocodestr:
            geocodeuri=geocodestr[0:geocodestr.find(">")].replace("<","").replace(">","").strip()
            geocodestr=geocodestr[geocodestr.find(">")+1:]
        thevalue=""
        if geocodeuri in Transformers.supported_geocodes:
            if geocodeuri=="http://opengis.net/ont/geocode/GeoURI":
                spl=geocodestr.replace("geo:","").split(",")
                if len(spl)==2:
                    thevalue=shapely.Point(float(spl[0]),float(spl[1]))
                elif len(spl)==3:
                    thevalue = shapely.Point(float(spl[0]), float(spl[1]),float(spl[2]))
            elif geocodeuri=="http://opengis.net/ont/geocode/OpenLocationCode":
                thevalue=shapely.Point(openlocationcode.decode(geocodestr).latlng())
            elif geocodeuri=="http://opengis.net/ont/geocode/GeoHash-36":
                decoded=pygeohash.decode(geocodestr)
                thevalue=shapely.Point(decoded.latitude, decoded.longitude)
        return thevalue

    ## Transforms a given DGGS representation to a vector geometry.
    #  @param dggsstr The DGGS representation to transform
    #  @param dggsuri The URI identifying the DGGS. May also be extracted from the geocode string itself if present
    #  @returns The converted geometry
    @staticmethod
    def dggsToGeom(dggsstr,dggsuri=""):
        dggsstr=dggsstr.replace("CELLLIST","").replace("CELL","").replace("(","[").replace(")","]").replace("'","\"")
        if "<" in dggsstr and ">" in dggsstr:
            dggsuri=dggsstr[0:dggsstr.find(">")].replace("<","").replace(">","").strip()
            dggsstr=dggsstr[dggsstr.find(">")+1:]
        dggsdict=json.loads(dggsstr)
        thevalue=""
        for dggsurisup in Transformers.supported_dggs:
            if dggsuri.startswith(dggsurisup.replace("{RESOLUTION}","")):
                thevalue=str(h3.cells_to_geo(dggsdict)).replace("(","[").replace(")","]").replace("'","\"").replace("],","]").replace("] [","], [")
                thevalue=shapely.ops.transform(lambda x, y: (y, x),shapely.from_geojson(thevalue))
        return thevalue

## Utilities to get attributes from SRS
class SRSUtils:

    ureg = UnitRegistry()

    unitsshort = {
        "m": "om:meter",
        "metre" : "om:metre",
        "grad":"om:degree",
        "degree" : "om:degree",
        "ft": "om:foot",
        "us-ft": "om:usfoot"
    }

    uniturisToPint={
        "http://qudt.org/vocab/unit/AC":"acre",
        "http://qudt.org/vocab/unit/MI":"mile",
        "http://qudt.org/vocab/unit/M": "meter",
        "http://qudt.org/vocab/unit/M2": "meter ** 2",
        "http://qudt.org/vocab/unit/M3": "meter ** 3",
        "http://www.opengis.net/def/uom/OGC/1.0/meter": "meter",
        "http://dbpedia.org/resource/Metre":"meter",
        "http://www.wikidata.org/entity/Q81292":"acre",
        "http://www.wikidata.org/entity/Q192624":"meter",
        "http://www.wikidata.org/entity/Q25343":"meter ** 2",
        "http://www.wikidata.org/wiki/Q25517":"meter ** 3",
        "http://www.wikidata.org/entity/Q828224":"kilometer",
        "http://www.wikidata.org/entity/Q253276": "mile",
        "https://si-digital-framework.org/SI/units/metre":"meter",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/degree": "degree",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/kilometer": "kilometer",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/meter": "meter",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/metre": "meter",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/mile": "mile",
    }

    uniturisToUnit={
        "http://qudt.org/vocab/unit/AC":"acre",
        "http://qudt.org/vocab/unit/MI":"mile",
        "http://qudt.org/vocab/unit/M": "meter",
        "http://qudt.org/vocab/unit/M2": "squaremeter",
        "http://qudt.org/vocab/unit/M3": "cubicmeter",
        "http://www.opengis.net/def/uom/OGC/1.0/meter": "meter",
        "http://dbpedia.org/resource/Metre":"meter",
        "http://www.wikidata.org/entity/Q81292":"acre",
        "http://www.wikidata.org/entity/Q192624":"meter",
        "http://www.wikidata.org/entity/Q25343":"squaremeter",
        "http://www.wikidata.org/wiki/Q25517":"cubicmeter",
        "http://www.wikidata.org/entity/Q828224":"kilometer",
        "http://www.wikidata.org/entity/Q253276": "mile",
        "https://si-digital-framework.org/SI/units/metre":"meter",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/degree": "degree",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/kilometer": "kilometer",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/meter": "meter",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/metre": "meter",
        "http://www.ontology-of-units-of-measure.org/resource/om-2/mile": "mile",
    }



    @staticmethod
    def getUnitsFromSRS(srsuri):
        curcrs = CRS.from_epsg(srsuri)
        unitres = []
        for ax in curcrs.coordinate_system.axis_list:
            if ax.unit_name in SRSUtils.unitsshort:
                unitres.append(SRSUtils.ureg.parse_expression(SRSUtils.unitsshort[ax.unit_name].replace("om:", "")))
        return unitres

    @staticmethod
    def getEastingFromSRS(srsuri):
        curcrs = CRS.from_epsg(srsuri)
        unitres = []
        for ax in curcrs.coordinate_system.axis_list:
            if ax.unit_name in SRSUtils.unitsshort:
                unitres.append(SRSUtils.ureg.parse_expression(SRSUtils.unitsshort[ax.unit_name].replace("om:", "")))
        return unitres

    @staticmethod
    def convertMetricToUnit(thevalue,metricunit,targetunit):
        if metricunit in SRSUtils.uniturisToPint and targetunit in SRSUtils.uniturisToPint:
            thevalue_withunit=thevalue*SRSUtils.ureg.parse_expression(SRSUtils.uniturisToPint[metricunit])
            return thevalue_withunit.to(SRSUtils.ureg.parse_expression(SRSUtils.uniturisToPint[targetunit]).units).magnitude
        return None


## Utilities for the conversion between literal and geometry objects
class LiteralUtils:

    #Literals which may only represent 3D geometries
    literals3d={GEO+"plyLiteral",GEO+"objLiteral",GEO+"gltfLiteral"}

    ## Extrudes a 2D geometry to a 3D geometry of depth 1.
    #  @param literal The geometry
    #  @returns An extruded trimesh geometry
    @staticmethod
    def createGeometry3D(shapelygeom):
        # print("CREATE3D")
        # print(shapelygeom.geom_type)
        # ress=trimesh.creation.triangulate_polygon(shapelygeom)
        ress = trimesh.creation.extrude_polygon(shapelygeom, 1)
        # print(shapelygeom)
        # print(ress)
        return ress

    ## Converts a WKT literal to a geometry object .
    #  @param literal The WKT literal
    #  @returns A geometry representing the contents of the given WKT literal
    @staticmethod
    def processWKTLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=WKTLiteral)

    ## Converts a GML literal to a geometry object .
    #  @param literal The GML literal
    #  @returns A geometry representing the contents of the given GML literal
    @staticmethod
    def processGMLLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GMLLiteral)

    ## Converts a KML literal to a geometry object .
    #  @param literal The KML literal
    #  @returns A geometry representing the contents of the given KML literal
    @staticmethod
    def processKMLLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=KMLLiteral)

    ## Converts a DGGS literal to a geometry object .
    #  @param literal The DGGS literal
    #  @returns A geometry representing the contents of the given DGGS literal
    @staticmethod
    def processDGGSLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=DGGSLiteral)

    ## Converts an GeoJSON literal to a geometry object .
    #  @param literal The GeoJSON literal
    #  @returns A geometry representing the contents of the given GeoJSON literal
    @staticmethod
    def processGeoJSONLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEOJSONLiteral)

    ## Converts an GLTF literal to a geometry object .
    #  @param literal The GLTF literal
    #  @returns A geometry representing the contents of the given GLTF literal
    @staticmethod
    def processGLTFLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GLTFLiteral,create3D=True)

    ## Converts an PLY literal to a geometry object .
    #  @param literal The PLY literal
    #  @returns A geometry representing the contents of the given PLY literal
    @staticmethod
    def processPLYLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=PLYLiteral,create3D=True)

    ## Converts an OBJ literal to a geometry object .
    #  @param literal The OBJ literal
    #  @returns A geometry representing the contents of the given OBJ literal
    @staticmethod
    def processOBJLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=OBJLiteral,create3D=True)

    ## Converts a WKB literal to a geometry object .
    #  @param literal The WKB literal
    #  @returns A geometry representing the contents of the given WKB literal
    @staticmethod
    def processWKBLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=WKBLiteral)

    @staticmethod
    def getBBOXFromLiteralType(geom):
        if isinstance(geom,trimesh.Trimesh):
            return geom.bounding_box_oriented
        else:
            return shapely.bounds(geom)

    ## Converts a geometry literal to a geometry object .
    #  @param literal The geometry literal or a string  representation of it
    #  @param datatype The datatype of the geometry literal if it is not given or a string representation was given as a parameter
    #  @param create3D Indicates whether the function calling this function demands a 3D representation of the geometry
    #  @param normsrs Indicates whether the created geometry should be normalized to a specific SRS
    #  @returns A geometry representing the contents of the given geometry literal
    @staticmethod
    def processLiteralTypeToGeom(literal, datatype=None,create3D=False, normsrs=None):
        if not isinstance(literal, Literal) and datatype is None:
            print(str(literal))
            raise ValueError("The " + str(literal) + " is not a literal!")
        if datatype is None:
            dtype = str(literal.datatype)
        else:
            dtype = str(datatype)
        lstring = str(literal).strip()
        #print(literal)
        #print(dtype)
        #print("LString: "+str(lstring))
        if str(dtype) == WKTLiteral:
            if lstring.startswith("<"):
                srsuri = lstring[0:lstring.find(">")].replace("<", "").replace(">", "")
                gstring = lstring[lstring.find(">") + 1:].strip()
                #print("GString: "+str(gstring))
                geo = shapely.from_wkt(gstring)
                srid = srsuri[srsuri.rfind("/") + 1:]
                if srid.isnumeric():
                    shapely.set_srid(geo, int(srid))
                #elif srid == "CRS84":
                #    shapely.set_srid(geo, 4326)
                if normsrs is not None:
                    geo = Transformers.transformToSRS(geo, srsuri, str(normsrs))
                    srsuri = normsrs
                if create3D:
                    return LiteralUtils.createGeometry3D(geo), srsuri
                return (geo, srsuri)
            else:
                geo = shapely.from_wkt(str(lstring))
                shapely.set_srid(geo, 4326)
                srsuri = CRS84URI
                if normsrs is not None:
                    geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                    srsuri = normsrs
                if create3D:
                    return (LiteralUtils.createGeometry3D(geo), srsuri)
                return (geo, srsuri)
        elif dtype == WKBLiteral:
            geo = shapely.from_wkb(lstring)
            shapely.set_srid(geo, 4326)
            srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return (LiteralUtils.createGeometry3D(geo), srsuri)
            return (geo, srsuri)
        elif dtype == GMLLiteral:
            gjson = None
            if "<gml:posList></gml:posList>" in lstring or "<posList></posList>" in lstring or "<gml:pos></gml:pos>" in lstring or "<pos></pos>" in lstring:
                if "LineString" in lstring:
                    geo = shapely.empty(2, shapely.GeometryType.LINESTRING)[0]
                elif "Point" in lstring:
                    geo = shapely.empty(2, shapely.GeometryType.POINT)[0]
                elif "Polygon" in lstring:
                    geo = shapely.empty(2, shapely.GeometryType.POLYGON)[0]
            else:
                gjson = pygml.parse(lstring.replace("http://www.opengis.net/def/crs/OGC/1.3/CRS84",
                                                    "urn:ogc:def:crs:OGC::CRS84")).geometry
                geo = shapely.geometry.shape(gjson)
            if gjson is not None and "crs" in gjson and "properties" in gjson["crs"] and "name" in gjson["crs"][
                "properties"]:
                srid = gjson["crs"]["properties"]["name"]
                if not srid.startswith("urn:"):
                    if srid.startswith("http"):
                        srid = srid[srid.rfind("/") + 1:]
                    else:
                        srid = gjson["crs"]["properties"]["name"][gjson["crs"]["properties"]["name"].rfind(":") + 1]
                    try:
                        shapely.set_srid(geo, int(srid))
                    except ValueError:
                        pass
                    srsuri = "http://www.opengis.net/def/crs/EPSG/0/" + str(srid)
                else:
                    srsuri = srid
            else:
                shapely.set_srid(geo, 4326)
                srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, srsuri, str(normsrs))
                srsuri = normsrs
            if create3D:
                return (LiteralUtils.createGeometry3D(geo), srsuri)
            return (geo, srsuri)
        elif dtype == GEOJSONLiteral:
            geo = shapely.from_geojson(lstring)
            shapely.set_srid(geo, 4326)
            srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return LiteralUtils.createGeometry3D(geo), srsuri
            return geo, srsuri
        elif dtype==GEOYAMLLiteral:
            geo=shapely.from_geojson(json.dumps(yaml.safe_load(lstring)))
            shapely.set_srid(geo, 4326)
            srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return LiteralUtils.createGeometry3D(geo), srsuri
            return geo, srsuri
        elif dtype == JSONFGLiteral:
            geo = shapely.from_geojson(lstring)
            if "coordRefSystem" in geo:
                shapely.set_srid(geo, 4326)
                srsuri = CRS84URI
            else:
                shapely.set_srid(geo, 4326)
                srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return LiteralUtils.createGeometry3D(geo), srsuri
            return geo, srsuri
        elif dtype == KMLLiteral:
            if not lstring.startswith("<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Placemark>"):
                lstring = "<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Placemark>" + str(
                    lstring) + "</Placemark></kml>"
            if "<coordinates></coordinates>" in lstring:
                if "LineString" in lstring:
                    geo = shapely.empty(2, shapely.GeometryType.LINESTRING)[0]
                elif "Point" in lstring:
                    geo = shapely.empty(2, shapely.GeometryType.POINT)[0]
                elif "Polygon" in lstring:
                    geo = shapely.empty(2, shapely.GeometryType.POLYGON)[0]
            else:
                geo = shapely.geometry.shape(kml.KML.from_string(lstring).features[0].geometry)
            #print(geo)
            shapely.set_srid(geo, 4326)
            srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return (LiteralUtils.createGeometry3D(geo), srsuri)
            return (geo, srsuri)
        elif dtype == DGGSLiteral:
            geo = Transformers.dggsToGeom(lstring)
            return (geo, CRS84URI)
        elif dtype == PLYLiteral:
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="ply")
            return (geo, CRS84URI)
        elif dtype == OBJLiteral:
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="obj")
            return (geo, CRS84URI)
        elif dtype == GLTFLiteral:
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="gltf")
            return (geo, CRS84URI)
        elif dtype == XYZLiteral:
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="xyz")
            return (geo, CRS84URI)
        else:
            thelit = str(literal)
            if len(thelit) > 100:
                thelit = thelit[0:100]
            raise ValueError(
                "The literal " + thelit + " (" + str(literal.datatype) + ") is no known geometry literal type!"
            )

    ## Converts a geometry to a GeoJSON Literal.
    #  @param literal The GeoJSON literal
    #  @returns The resulting GeoJSON literal
    @staticmethod
    def processGeomToGeoJSONLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEOJSONLiteral,geomtup[1])

    ## Converts a geometry to a GLTF Literal.
    #  @param literal The GLTF literal
    #  @returns The resulting GLTF literal
    @staticmethod
    def processGeomToGLTFLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GLTFLiteral,geomtup[1])

    ## Converts a geometry to a GML Literal.
    #  @param literal The GML literal
    #  @returns The resulting GML literal
    @staticmethod
    def processGeomToGMLLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GMLLiteral,geomtup[1])

    ## Converts a geometry to a KML Literal.
    #  @param literal The KML literal
    #  @returns The resulting KML literal
    @staticmethod
    def processGeomToKMLLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], KMLLiteral,geomtup[1])

    ## Converts a geometry to a OBJ Literal.
    #  @param literal The OBJ literal
    #  @returns The resulting OBJ literal
    @staticmethod
    def processGeomToOBJLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], OBJLiteral,geomtup[1])

    ## Converts a geometry to a PLY Literal.
    #  @param literal The PLY literal
    #  @returns The resulting PLY literal
    @staticmethod
    def processGeomToPLYLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], PLYLiteral,geomtup[1])

    ## Converts a geometry to a WKB Literal.
    #  @param literal The WKB literal
    #  @returns The resulting WKB literal
    @staticmethod
    def processGeomToWKBLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], WKBLiteral,geomtup[1])

    ## Converts a geometry to a WKT Literal.
    #  @param literal The WKT literal
    #  @returns The resulting WKT literal
    @staticmethod
    def processGeomToWKTLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], WKTLiteral,geomtup[1])


        

    ## Converts a geometry to a geometry literal.
    #  @param geom The geometry to convert
    #  @param literaltype The literaltype to convert to
    #  @param thegeomsrs The SRS of the output geometry
    #  @returns A geometry literal in the required literal type and SRS
    @staticmethod
    def processGeomToLiteral(geom, literaltype, thegeomsrs="") -> Literal:
        #print("GEOMTOLIT: "+str(geom))
        #print(str(type(geom)))
        ltype = str(literaltype)
        if ltype == WKTLiteral:
            if thegeomsrs == "":
                return Literal("<" + CRS84URI + "> " + str(geom.wkt), datatype=literaltype)
            else:
                return Literal("<" + str(thegeomsrs) + "> " + str(geom.wkt), datatype=literaltype)
        elif ltype == GEOJSONLiteral:
            return Literal(str(shapely.io.to_geojson(geom)), datatype=literaltype)
        elif ltype == GEOYAMLLiteral:
            return Literal(str(yaml.dump(json.loads(shapely.io.to_geojson(geom)))), datatype=literaltype)
        elif ltype == GMLLiteral:
            return Literal(etree.tostring(encode_v32(json.loads(shapely.io.to_geojson(geom)), "ID"),encoding="unicode"), datatype=literaltype)
        elif ltype == JSONFGLiteral:
            thegeofg=json.loads(shapely.io.to_geojson(geom))
            thegeofg["coordRefSys"] = thegeomsrs
            thegeofg["conformsTo"] = ["http://www.opengis.net/spec/json-fg-1/1.0/conf/core",
                                    "http://www.opengis.net/spec/json-fg-1/1.0/conf/types-schemas"]
            return Literal(str(json.dumps(thegeofg)), datatype=literaltype)
        elif ltype == KMLLiteral:
            return Literal("<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Placemark>" + str(fastkml.geometry.create_kml_geometry(geom)) + "</Placemark></kml>", datatype=literaltype)
        elif ltype == WKBLiteral:
            return Literal(str(geom.wkb_hex), datatype=literaltype)
        elif ltype == SVGLiteral:
            return Literal(str(geom.svg()), datatype=literaltype)
        elif ltype == PLYLiteral:
            bio = BytesIO()
            ress=geom.export(bio, file_type="ply", encoding='ascii')
            return Literal(ress.decode("utf-8"), datatype=literaltype)
        elif ltype == OBJLiteral:
            bio = BytesIO()
            ress=geom.export(bio, file_type="obj", encoding='ascii')
            print("OBJ RESS")
            print(ress)
            #wrapper = TextIOWrapper(bio, encoding='utf-8')
            return Literal(ress.decode("utf-8"), datatype=literaltype)
        #elif ltype == XYZLiteral:
        #    bio = BytesIO()
        #    ress=geom.export(bio, file_type="xyz")
        #    #wrapper = TextIOWrapper(bio, encoding='utf-8')
        #    return Literal(ress.decode("utf-8"), datatype=literaltype)
        elif ltype == GLTFLiteral:
            bio = BytesIO()
            ress=geom.export(bio, file_type="gltf")
            print(ress)
            #print(json.dumps(ress))
            #wrapper = TextIOWrapper(bio, encoding='utf-8')
            return Literal(str(ress), datatype=literaltype)
        elif ltype == DGGSLiteral:
            return Literal(Transformers.transformToDGGS(geom,thegeomsrs),datatype=literaltype)
        elif ltype == GEOCODELiteral:
            return Literal(Transformers.transformToGeocode(geom,thegeomsrs),datatype=literaltype)
        else:
            raise ValueError(
                "The literal type " + str(literaltype) + " is not supported for geometry conversion!"
            )

    ## Converts a list of geometry literals to a list of geometries.
    #  @param literals The list of literalts to convert
    #  @param normalize Indicates whether the geometries should be harmonized to a SRS (per default the SRS of the first geometry)
    #  @param normsrs The SRS to normalize to
    #  @param create3D Indicates whether the geometries should be extruded to 3D
    #  @returns A list of geometries
    @staticmethod
    def processLiteralsToGeom(literals, normalize=False, normsrs=None, create3D=False):
        geoms = []
        first = True
        for lit in literals:
            if isinstance(lit, Literal):
                # print("NormSRS: "+str(normsrs))
                g = LiteralUtils.processLiteralTypeToGeom(lit, create3D=create3D, normsrs=normsrs)
                # print(g)

                if normalize and first and normsrs is None:
                    normsrs = str(g[1])
                    first = False
                    # g=(Transformers.transformToSRS(g[0], g[1], str(normsrs)), normsrs)
                geoms.append(g)
        # print(geoms)
        return geoms

class Handling3D:

    @staticmethod
    def identityMatrix(a: Literal):
        print("")

    @staticmethod
    def is3D(geom):
        if geom.has_z:
            return True
        return False

    @staticmethod
    def bbox3D(geom):
        bbox2d=shapely.envelope(geom).bounds
        minZ=Handling3D.minZ(geom)
        maxZ=Handling3D.maxZ(geom)
        minX=bbox2d[0]
        minY=bbox2d[1]
        maxX=bbox2d[2]
        maxY=bbox2d[3]
        return shapely.from_wkt("POLYGON Z(("+str(minX)+" "+str(minY)+" "+str(minZ)+", "
                                +str(maxX)+" "+str(maxY)+" "+str(minZ)+", "
                                +str(minX)+" "+str(maxY)+" "+str(minZ)+", "
                                +str(minX)+" "+str(minY)+" "+str(maxZ)+", "
                                +str(maxX)+" "+str(minY)+" "+str(maxZ)+", "
                                +str(maxX)+" "+str(maxY)+" "+str(maxZ)+", "
                                +str(minX)+" "+str(maxY)+" "+str(maxZ)+", "
                                +str(minX)+" "+str(minY)+" "+str(minZ)+"))")

    @staticmethod
    def centroid3D(geom):
        g1list = shapely.get_coordinates(geom, include_z=True).tolist()
        centroid2d=shapely.centroid(geom)
        zadded=0
        for p1 in g1list:
            pt1 = shapely.geometry.Point(p1)
            zadded+=pt1.z
        return shapely.geometry.Point([centroid2d.x,centroid2d.y,zadded/len(g1list)])

    @staticmethod
    def geometricMedian(geom):
        if Handling3D.is3D(geom):
            points=shapely.get_coordinates(geom, include_z=True).tolist()
        else:
            points = shapely.get_coordinates(geom, include_z=False).tolist()
        dim = len(points[0])
        tol = 1e-9
        max_iter = 1000
        current = [sum(p[i] for p in points) / len(points) for i in range(dim)]
        for _ in range(max_iter):
            numerator = [0.0] * dim
            denominator = 0.0
            #print(points)
            for point in points:
                #print(point)
                dist = math.sqrt(sum((point[i] - current[i]) ** 2 for i in range(dim)))
                # Handle coincidence with a data point
                if dist < tol:
                    return shapely.geometry.Point(point[0],point[1])
                weight = 1.0 / dist
                for i in range(dim):
                    numerator[i] += weight * point[i]
                denominator += weight
            new_point = [x / denominator for x in numerator]
            movement = math.sqrt(sum((new_point[i] - current[i]) ** 2 for i in range(dim)))
            if movement < tol:
                return shapely.geometry.Point(new_point[0],new_point[1])
            current = new_point
        if dim==2:
            return shapely.geometry.Point(current[0], current[1])
        else:
            return shapely.geometry.Point(current[0], current[1], current[2])

    @staticmethod
    def distanceWrapper(pt1,pt2,is3D):
        if is3D:
            return math.sqrt(((pt2.x-pt1.x)**2)+((pt2.y-pt1.y)**2)+((pt2.z-pt1.z)**2))
        return shapely.distance(pt1,pt2)

    @staticmethod
    def length3D(coords):
        length3d = 0
        i=0
        while i < len(coords):
            coord1=coords[i]
            coord2=coords[i+1]
            dx = coord1[0] - coord2[0]
            dy = coord1[1] - coord2[1]
            dz = coord1[2] - coord2[2]
            length3d += math.sqrt(dx * dx + dy * dy + dz * dz)
            i+=2
        return length3d

    @staticmethod
    def distance3DAware(geom1,geom2,minDist=True):
        g1list = shapely.get_coordinates(geom1, include_z=True).tolist()
        g2list = shapely.get_coordinates(geom2, include_z=True).tolist()
        if minDist==False:
            distance = float("-inf")
        else:
            distance = float("inf")
        for p1 in g1list:
            for p2 in g2list:
                pt1=shapely.geometry.Point(p1)
                pt2 = shapely.geometry.Point(p2)
                dist=math.sqrt(((pt2.x-pt1.x)**2)+((pt2.y-pt1.y)**2)+((pt2.z-pt1.z)**2))
                if minDist and dist < distance:
                    distance = dist
                elif not minDist and dist > distance:
                    distance=dist
        return distance


    @staticmethod
    def minZ(thegeom):
        clist = shapely.get_coordinates(thegeom, include_z=True).tolist()
        flinf = float("inf")
        minZ = flinf
        for c in clist:
            #print(c)
            if c[2] != math.nan and minZ > c[2]:
                minZ = c[2]
        if minZ == flinf:
            minZ = "NaN"
        return minZ

    @staticmethod
    def maxZ(thegeom):
        clist = shapely.get_coordinates(thegeom, include_z=True).tolist()
        flinf = -float("inf")
        maxZ = flinf
        for c in clist:
            if c[2] != math.nan and maxZ < c[2]:
                maxZ = c[2]
        if maxZ == flinf:
            maxZ = "NaN"
        return maxZ

class SerializationFunctions:

    ## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asDGGS">geof:asDGGS</a>: Converts a geometry literal to a DGGS literal .
    #  @param a The geometry literal
    #  @param dggsType The DGGS type described by a URI
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#dggsLiteral">geo:dggsLiteral</a>
    @staticmethod
    def asDGGS(a: Literal, dggsType) -> Literal:
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        # print(a: Literal)
        # print(dggsType)
        # print(Transformers.transformToDGGS(thegeom, dggsType))
        return Literal(Transformers.transformToDGGS(thegeom, dggsType), datatype=DGGSLiteral)

    ## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asGeoJSON">geof:asGeoJSON</a>: Converts a geometry literal to a GeoJSON literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#geoJSONLiteral">geo:geoJSONLiteral</a>
    @staticmethod
    def asGeoJSON(a: Literal) -> Literal:
        if a.datatype == GEOJSONLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(thegeom, GEOJSONLiteral, thegeomsrs)

    ## Converts a geometry literal to a GeoYAML literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#geoYAMLLiteral">geo:geoYAMLLiteral</a>
    @staticmethod
    def asGeoYAML(a: Literal) -> Literal:
        if a.datatype == GEOYAMLLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(thegeom, GEOYAMLLiteral, thegeomsrs)

    ## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asGeoJSON">geof:asGeoJSON</a>: Converts a geometry literal to a GeoJSON literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#geoJSONLiteral">geo:geoJSONLiteral</a>
    @staticmethod
    def asJSONFG(a: Literal) -> Literal:
        if a.datatype == JSONFGLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(thegeom, JSONFGLiteral, thegeomsrs)

    ## Converts a geometry literal to a GLTF literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#gltfLiteral">geo:gltfLiteral</a>
    @staticmethod
    def asGLTF(a: Literal) -> Literal:
        if a.datatype == GLTFLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
        return LiteralUtils.processGeomToLiteral(thegeom, GLTFLiteral, thegeomsrs)

    ## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asGeocode">geof:asGeocode</a>: Converts a geometry literal to a Geocode literal .
    #  @param a The geometry literal
    #  @param geocodeURI The Geocode type described by a URI
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#geocodeLiteral">geo:geocodeLiteral</a>
    @staticmethod
    def asGeocode(a: Literal, geocodeURI) -> Literal:
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        print(thegeom)
        print(geocodeURI)
        return Literal(Transformers.transformToGeocode(thegeom, str(geocodeURI)),
                       datatype=GEOCODELiteral)

    ## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asGML">geof:asGML</a>: Converts a geometry literal to a GML literal preserving its coordinate reference system.
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#gmlLiteral">geo:gmlLiteral</a>
    @staticmethod
    def asGML(a: Literal) -> Literal:
        if a.datatype == GMLLiteral:
            return a
        thegeom, thegeomsrs = a.value  # LiteralUtils.processLiteralTypeToGeom(a)
        print("THE GEOM GML: " + str(thegeom))
        return LiteralUtils.processGeomToLiteral(thegeom, GMLLiteral, thegeomsrs)

    ## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asKML">geof:asKML</a>: Converts a geometry literal to a KML literal.
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#kmlLiteral">geo:kmlLiteral</a>
    @staticmethod
    def asKML(a: Literal) -> Literal:
        if a.datatype == KMLLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(thegeom, KMLLiteral, thegeomsrs)

    ## Converts a geometry literal to a OBJ literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#objLiteral">geo:objLiteral</a>
    @staticmethod
    def asOBJ(a: Literal) -> Literal:
        if a.datatype == OBJLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
        return LiteralUtils.processGeomToLiteral(thegeom, OBJLiteral, thegeomsrs)

    ## Converts a geometry literal to a PLY literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#objLiteral">geo:plyLiteral</a>
    @staticmethod
    def asPLY(a: Literal) -> Literal:
        if a.datatype == PLYLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
        return LiteralUtils.processGeomToLiteral(thegeom, PLYLiteral, thegeomsrs)

    ## Converts a geometry literal to a SVG literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#svgLiteral">geo:svgLiteral</a>
    @staticmethod
    def asSVG(a: Literal) -> Literal:
        if a.datatype == SVGLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(thegeom, SVGLiteral, thegeomsrs)

    ## Converts a geometry literal to a XYZ literal .
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#xyzLiteral">geo:xyzLiteral</a>
    @staticmethod
    def asXYZ(a: Literal) -> Literal:
        if a.datatype == XYZLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
        return LiteralUtils.processGeomToLiteral(thegeom, XYZLiteral, thegeomsrs)

    ## Converts a geometry literal to a WKB literal.
    #  Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asWKB">geof:asWKB</a>
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#wkbLiteral">geo:wkbLiteral</a>
    @staticmethod
    def asWKB(a: Literal) -> Literal:
        if a.datatype == WKBLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(thegeom, WKBLiteral, thegeomsrs)

    ## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asWKT">geof:asWKT</a>: Converts a geometry literal to a WKT literal.
    #  @param a The geometry literal
    #  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#wktLiteral">geo:wktLiteral</a>
    @staticmethod
    def asWKT(a: Literal) -> Literal:
        if a.datatype == WKTLiteral:
            return a
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(thegeom, WKTLiteral, thegeomsrs)

def range_overlap(start1, end1, start2, end2):
    """how much does the range (start1, end1) overlap with (start2, end2)"""
    #print("Start1: "+str(start1)+" End1: "+str(end1)+"Start2: "+str(start2)+" End2: "+str(end2))
    if start1==start2 and end1==end2:
        return 100
    if start1==end1:
        end1=start1+0.1
    if start2==end2:
        end2=start2+0.1
    res=max(max((end2-start1), 0) - max((end2-end1), 0) - max((start2-start1), 0), 0)
    #print(res)
    return res

## Calculates whether the first geometry is above the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is above the second geometry
def above(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        if Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
            # geom[0].maxY>geom[1].minY and
            geom1bounds = shapely.total_bounds(geoms[0])
            geom2bounds = shapely.total_bounds(geoms[1])
            rox = range_overlap(geom1bounds[0], geom1bounds[2], geom2bounds[0], geom2bounds[2])
            roz = range_overlap(Handling3D.minZ(geoms[0]), Handling3D.maxZ(geoms[0]), Handling3D.minZ(geoms[1]),
                                Handling3D.maxZ(geoms[1]))
            #print("ROX: "+str(rox))
            #print("ROZ: "+str(roz))
            #geom1bounds[3] > geom2bounds[1]
            return Literal(rox > 0 and roz > 0 and geom1bounds[3]>geom2bounds[1], datatype=XSD.boolean)
        else:
            #geom[0].maxY<geom[1].minY
            geom1bounds=shapely.total_bounds(geoms[0])
            geom2bounds=shapely.total_bounds(geoms[1])
            ro=range_overlap(geom1bounds[0],geom1bounds[2],geom2bounds[0],geom2bounds[2])
            #print("ROX: " + str(ro))
            #print(geom1bounds)
            #print(geom2bounds)
            #print(ro)
            #print(str(geom1bounds[3])+" < "+str(geom2bounds[1])+" = "+str(geom1bounds[3]<geom2bounds[1]))
            #print("GEOM1 ABOVE GEOM2? "+str(ro>0 and geom1bounds[3]<geom2bounds[1]))
            return Literal(ro>0 and geom1bounds[3]>geom2bounds[1], datatype=XSD.boolean)

## Calculates whether the first 3D geometry is above the 3D second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is above the second geometry
def above3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None and Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
        #geom[0].maxY>geom[1].minY and
        geom1bounds=shapely.total_bounds(geoms[0])
        geom2bounds=shapely.total_bounds(geoms[1])
        rox=range_overlap(geom1bounds[0],geom1bounds[2],geom2bounds[0],geom2bounds[2])
        roz=range_overlap(Handling3D.minZ(geoms[0]),Handling3D.maxZ(geoms[0]),Handling3D.minZ(geoms[1]),Handling3D.maxZ(geoms[1]))
        return Literal(rox>0 and roz>0 and geom1bounds[3]>geom2bounds[1], datatype=XSD.boolean)
    raise ValueError("The provided input geometries were either not valid or not 3D")

## Adds a coordinate at the given index to the geometry
#  @param a The geometry literal
#  @param b The coordindate to add
#  @param poinindex The index at which the coordinate should be added
#  @returns The geometry with the added coordinate in the CRS and literal format of the input geometry
def addPoint(a: Literal, b:Literal, pointindex: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    theindex=int(pointindex.value)
    if geoms[1].geom_type == "Point":
        if geoms[0].geom_type == "Point":
            if theindex==0:
                coords = list(geoms[0].coords)
                coords.insert(theindex,geoms[1].coords[0])
                return LiteralUtils.processGeomToLiteral(shapely.geometry.LineString(coords), a.datatype)
            raise ValueError("Selected to remove a coordinate from a Point geometry with index greater 0")
        if geoms[0].geom_type == "LineString":
            coords=list(geoms[0].coords)
            coords.insert(theindex,geoms[1].coords[0])
            return LiteralUtils.processGeomToLiteral(shapely.geometry.LineString(coords), a.datatype)
        if geoms[0].geom_type == "Polygon":
            coords = list(geoms[0].exterior.coords)
            coords.insert(theindex,geoms[1].coords[0])
            if coords[0] != coords[-1]:
                coords[-1] = coords[0]
            return LiteralUtils.processGeomToLiteral(shapely.geometry.Polygon(coords), a.datatype)
    raise ValueError("This function is only support for Point, LineString and Polygon geometries")

def affineTransformation(a: Literal, matrix: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    splitted=str(matrix).replace("[","").replace("]","").split(" ")
    if len(splitted)==6 or len(splitted)==12:
        return Literal(shapely.affinity.affine_transform(thegeom, [float(i) for i in splitted]), datatype=XSD.double)
    raise ValueError("The transformation matrix did not meet the expected format  [a, b, d, e, xoff, yoff] or [a, b, c, d, e, f, g, h, i, xoff, yoff, zoff]")

## Appends a coordinate to a given geometry
#  @param a The geometry literal
#  @param b The point to append
#  @returns The geometry without repeated points in the CRS and literal format of the input geometry
def appendPoint(a: Literal, b:Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return addPoint(a,b,Literal(shapely.get_num_points(thegeom)-1,datatype=XSD.integer))

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/area">geof:area</a>: Calculates the area of a 2D geometry provided as a geometry literal .
#  @param a The geometry literal.
#  @param unit The unit in which to represent the area.
#  @returns The area as an <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def area(a: Literal, unit: Literal) -> Literal:
    if unit.value not in SRSUtils.uniturisToUnit:
        raise ValueError("The provided unit "+str(unit)+" is not a supported unit.\nSupported units: "+str(SRSUtils.uniturisToUnit.keys()))
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    thearea=shapely.area(normgeom)
    if SRSUtils.uniturisToUnit[unit.value]!="squaremeter":
        thearea=SRSUtils.convertMetricToUnit(thearea,"http://qudt.org/vocab/unit/M2",unit.value)
    return Literal(thearea, datatype=XSD.double)

## Calculates the azimuth of a 2D geometry provided as a geometry literal .
#  @param a The geometry literal.
#  @returns The azimuth as an <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def azimuth(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    minrect = thegeom.minimum_rotated_rectangle
    minrectb = minrect.boundary
    coords = [c for c in minrectb.coords]  # List the line coordinates
    segments = [shapely.geometry.LineString([a, b]) for a, b in zip(coords, coords[1:])]  # Create the four side lines.
    longest_segment = max(segments, key=lambda x: x.length)
    p1, p2 = [c for c in longest_segment.coords]  # List the start and end coordinates of it
    azimuthangle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
    return Literal(azimuthangle, datatype=XSD.double)



## Calculates whether the first geometry is behind the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is behind the second geometry
def behind(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None and Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
        #geom[0].maxZ<geom[1].minZ
        geom1bounds=shapely.total_bounds(geoms[0])
        geom2bounds = shapely.total_bounds(geoms[1])
        rox=range_overlap(geom1bounds[0],geom1bounds[2],geom2bounds[0],geom2bounds[2])
        roy=range_overlap(geom1bounds[1],geom1bounds[3],geom2bounds[1],geom2bounds[3])
        geom1maxZ=Handling3D.maxZ(geoms[0])
        geom2minZ=Handling3D.minZ(geoms[1])
        return Literal(rox>0 and roy>0 and geom1maxZ<geom2minZ, datatype=XSD.boolean)
    raise ValueError("At least one of the input geometries are not valid or not in 3D")

## Calculates whether the first geometry is below the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is below the second geometry
def below(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        if Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
            if geoms[0] is not None and geoms[1] is not None:
                # geom[0].maxY<geom[1].minY
                geom1bounds = shapely.total_bounds(geoms[0])
                geom2bounds = shapely.total_bounds(geoms[1])
                rox = range_overlap(geom1bounds[0], geom1bounds[2], geom2bounds[0], geom2bounds[2])
                roz = range_overlap(Handling3D.minZ(geoms[0]), Handling3D.maxZ(geoms[0]), Handling3D.minZ(geoms[1]),
                                    Handling3D.maxZ(geoms[1]))
                return Literal(rox > 0 and roz > 0 and geom1bounds[3] < geom2bounds[1], datatype=XSD.boolean)
        else:
            #geom[0].maxY<geom[1].minY
            geom1bounds=shapely.total_bounds(geoms[0])
            geom2bounds=shapely.total_bounds(geoms[1])
            ro=range_overlap(geom1bounds[0],geom1bounds[2],geom2bounds[0],geom2bounds[2])
            #print(geom1bounds)
            #print(geom2bounds)
            #print(ro)
            #print(str(geom1bounds[3])+" < "+str(geom2bounds[1])+" = "+str(geom1bounds[3]<geom2bounds[1]))
            #print("GEOM1 BELOW GEOM2? "+str(ro>0 and geom1bounds[3]<geom2bounds[1]))
            return Literal(ro>0 and geom1bounds[3]<geom2bounds[1], datatype=XSD.boolean)
    raise ValueError("At least one of the input geometries are not valid")

## Calculates whether the first 3D geometry is below the 3D second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is below the second geometry
def below3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None and Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
        geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
        if geoms[0] is not None and geoms[1] is not None:
            #geom[0].maxY<geom[1].minY
            geom1bounds=shapely.total_bounds(geoms[0])
            geom2bounds=shapely.total_bounds(geoms[1])
            rox=range_overlap(geom1bounds[0],geom1bounds[2],geom2bounds[0],geom2bounds[2])
            roz=range_overlap(Handling3D.minZ(geoms[0]),Handling3D.maxZ(geoms[0]),Handling3D.minZ(geoms[1]),Handling3D.maxZ(geoms[1]))
            return Literal(rox>0 and roz>0 and geom1bounds[3]<geom2bounds[1], datatype=XSD.boolean)
    raise ValueError("At least one of the input geometries are not valid or 3D")

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/boundary">geof:boundary</a>: Calculates the boundary of a geometry literal.
#  @param a The geometry literal
#  @returns The geometry as a geometry literal in the CRS and literal format of the input geometry
def boundary(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.boundary(thegeom), a.datatype, thegeomsrs)

## Retrieves the diagonal of the bounding box between the minimum coordinate and the maximum coordinate
#  @param a The input geometry literal
#  @returns The bounding diagonal
def boundingDiagonal(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    thebounds=thegeom.bounds
    return LiteralUtils.processGeomToLiteral(shapely.geometry.LineString([[thebounds[0],thebounds[1]],[thebounds[2],thebounds[3]]]), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/boundingCircle">geof:boundingCircle</a>: Calculates the minimum bounding circle of a geometry literal.
#  @param a The geometry literal
#  @returns The bounding circle as a geometry literal in the CRS and literal format of the input geometry
def boundingCircle(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.minimum_bounding_circle(thegeom), a.datatype, thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/buffer">geof:buffer</a>: Calculates the buffer of a geometry literal with a given radius and a given unit.
#  @param a The geometry literal
#  @param radius The buffer radius
#  @param unit the radius unit
#  @returns The buffer as a geometry literal in the CRS and literal format of the input geometry
def buffer(a: Literal, radius: Literal, unit: Literal="") -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if isinstance(radius, Literal) and radius.datatype == XSD.double:
        return LiteralUtils.processGeomToLiteral(shapely.buffer(thegeom, float(radius)), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/centroid">geof:centroid</a>: Calculates the centroid of a geometry literal.
#  @param a The geometry literal
#  @returns The centroid as a geometry literal in the CRS of the input geometry
def centroid(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print(thegeom)
    if Handling3D.is3D(thegeom):
        return LiteralUtils.processGeomToLiteral(Handling3D.centroid3D(thegeom),a.datatype, thegeomsrs)
    return LiteralUtils.processGeomToLiteral(thegeom.centroid, a.datatype, thegeomsrs)


def clipByRect(a: Literal, b:Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    bounds=geoms[1].bounds
    clipped=shapely.clip_by_rect(geoms[0],bounds[0],bounds[1],bounds[2],bounds[3])
    return LiteralUtils.processGeomToLiteral(clipped, a.datatype, "")


## Retrieves the point on the second geometry parameter which is closest to the first geometry
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The closest point on the first geometry to the second geometry as a geometry literal of the same type and CRS as the first input geometry
def closestPoint(a: Literal, b: Literal) -> Literal:
    print(a)
    print(b)
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    print(geoms)
    is3D=Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1])
    g1list = shapely.get_coordinates(geoms[0], include_z=is3D).tolist()
    g2list = shapely.get_coordinates(geoms[1], include_z=is3D).tolist()
    mindistance=float("inf")
    closest=None
    for p1 in g1list:
        cp = shapely.geometry.Point(p1)
        for p2 in g2list:
            dist = Handling3D.distanceWrapper(cp, shapely.geometry.Point(p2),is3D)
            if dist<mindistance:
                mindistance=dist
                closest=cp
    print("CLOSEST: "+str(closest))
    if closest is not None:
        return LiteralUtils.processGeomToLiteral(closest,a.datatype,"")

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfContains">geof:sfContains</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehContains">geof:ehContains</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8ntppi">geof:rcc8ntppi</a>: Calculates whether the first geometry contains the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry contains the second geometry
def contains(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.contains(geoms[0], geoms[1]), datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/concaveHull">geof:concaveHull</a>: Calculates the concave hull of a geometry literal.
#  @param a The geometry literal
#  @returns The concave hull as a geometry literal in the format and CRS of the input geometry
def concaveHull(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.concave_hull(thegeom), a.datatype, thegeomsrs)


## Calculates s triangulation using the constrained delaunay algorithm.
#  @param a The geometry literal
#  @returns The constrained delaunay triangulation result as a geometry literal in the format and CRS of the input geometry
def constrainedDelaunay(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.constrained_delaunay_triangles(thegeom), a.datatype, thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/convexHull">geof:convexHull</a>: Calculates the convex hull of a geometry literal.
#  @param a The geometry literal
#  @returns The convex hull as a geometry literal in the CRS of the input geometry
def convexHull(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom.convex_hull, a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/cooordinateDimension">geof:coordinateDimension</a>: Calculates the coordinate dimension of a geometry literal.
#  @param a The geometry literal
#  @returns The coordinate dimension as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#integer">xsd:integer</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def coordinateDimension(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.get_coordinate_dimension(thegeom), datatype=XSD.integer)


def compactnessRatio(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    p = thegeom.length
    a = thegeom.area
    return Literal(str(1 / (p / (2 * math.pi * math.sqrt(a / math.pi)))), datatype=XSD.double)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehCovers">geof:ehCovers</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8tppi">geof:rcc8tppi</a>: Calculates whether the first geometry covers the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry covers the second geometry
def covers(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.covers(geoms[0], geoms[1]), datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehCoveredBy">geof:ehCoveredBy</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8tppi">geof:rcc8tppi</a>: Calculates whether the first geometry is covered by the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is covered by the second geometry
def coveredBy(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.covered_by(geoms[0], geoms[1]), datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfCrosses">geof:sfCrosses</a>: Calculates whether the first geometry crosses the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry crosses the second geometry
def crosses(a: Literal, b: Literal) -> Literal | None | Any:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.crosses(geoms[0], geoms[1]), datatype=XSD.boolean)

## Calculates a delaunay triangulation on a given geometry.
#  @param a The geometry literal
#  @returns The delaunay triangulation result as a geometry literal in the format and CRS of the input geometry
def delaunayTriangles(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.delaunay_triangles(thegeom), a.datatype, thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfDisjoint">geof:sfDisjoint</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehDisjoint">geof:ehDisjoint</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8dc">geof:rcc8dc</a>: Calculates whether the two input geometries are disjoint.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the two geometries are disjoint
def disjoint(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.disjoint(geoms[0], geoms[1]), datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/difference">geof:difference</a>: Calculates the difference of two geometry literals.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The difference as a geometry literal in the CRS and literal format of the first input geometry
def difference(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    print(geomtps)
    print(shapely.difference(geomtps[0][0], geomtps[1][0]))
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.difference(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])

def difference3D(a: Literal, b: Literal) -> Literal:
    print("DIFF 3D")
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, create3D=True)))[0]
    """
    print("GEOMS: "+str(geoms))
    diff=geoms[0].difference(geoms[1])
    print("DIFF: "+str(diff))
    bio = BytesIO()
    diff.export(bio, file_type="ply", encoding='ascii')
    res=bio.getvalue().decode("utf-8")
    print("DIFF AS PLY: "+str(res))
    print(geoms[0].difference(geoms[1]).volume)
    """
    if geoms[0] is not None and geoms[1] is not None:
        diff=geoms[0].difference(geoms[1])
        bio = BytesIO()
        diff.export(bio, file_type="ply", encoding='ascii')
        res = bio.getvalue().decode("utf-8")
        return LiteralUtils.processGeomToLiteral(diff,a.datatype)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/distance">geof:distance</a>: Retrieves the distance between two geometries.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @param units The unit in which to return the distance as a URI
#  @returns The distance as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def distance(a: Literal, b: Literal, units: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        if Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
            return Literal(Handling3D.distance3D(geoms[0],geoms[1]), datatype=XSD.double)
        return Literal(shapely.distance(geoms[0], geoms[1]), datatype=XSD.double)
    raise ValueError("Invalid parameters, e.g. invalid geometry literals were provided for function geof:distance")

## Retrieves the distance between two geometries in 3D.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The distance as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def distance3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(Handling3D.distance3D(geoms[0],geoms[1]), datatype=XSD.double)
    raise ValueError("Invalid parameters, e.g. invalid geometry literals were provided for function geof:distance3D")

## Extracts the last point of an input geometry.
#  @param a The geometry literal
#  @returns The end point as a geometry literal in the CRS and literal format of the input geometry
def endPoint(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.Point(shapely.get_coordinates(thegeom)[-1]), a.datatype,
                                             thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfEquals">geof:sfEquals</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehEquals">geof:ehEquals</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8eq">geof:rcc8eq</a>: Calculates whether the two input geometries are equal.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the two geometries are equal
def equals(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.equals(geoms[0], geoms[1]), datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/envelope">geof:envelope</a>: Calculates a bounding box around the given geometry
#  @param a The geometry literal
#  @returns The envelope of the given geometry as a geometry literal of the same type and CRS as the input geometry
def envelope(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if Handling3D.is3D(thegeom):
        return LiteralUtils.processGeomToLiteral(Handling3D.bbox3D(thegeom), a.datatype, thegeomsrs)
    return LiteralUtils.processGeomToLiteral(thegeom.envelope, a.datatype, thegeomsrs)

## Extrudes a geometry to a fixed Z value.
#  @param a The geometry literal
#  @param The extrusion value
#  @returns The extruded geometry as a geometry literal of the same type and CRS as the input geometry
def extrude(a: Literal, extrudeval: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.force_3d(shapely.force_2d(thegeom), extrudeval), a.datatype,
                                             thegeomsrs)

## Extracts an exerior ring from a geometry if it exists
#  @param a The geometry literal
#  @returns The exterior ring geometry as a geometry literal of the same type and CRS as the input geometry
def exteriorRing(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.get_exterior_ring(thegeom), a.datatype, thegeomsrs)

## Retrieves the farthest coordinate on a geometry to a given point
#  @param a The given point
#  @param b The geometry to calculate the farthest coordinate on.
#  @returns The farthest coordinate a a geometry lof the same type and CRS as the first input geometry
def farthestCoordinate(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    print(geoms)
    if geoms[0] is not None and geoms[0].geom_type!="Point":
        raise ValueError("The first parameter of the function geof:farthestCoordinate should represent a point geometry")
    is3D=Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1])
    g1list = shapely.get_coordinates(geoms[0], include_z=is3D).tolist()
    g2list = shapely.get_coordinates(geoms[1], include_z=is3D).tolist()
    maxdistance=float("-inf")
    farthest=None
    print(g1list)
    print(g2list)
    for p1 in g1list:
        p1p=shapely.geometry.Point(p1)
        for p2 in g2list:
            cp=shapely.geometry.Point(p2)
            dist=Handling3D.distanceWrapper(p1p,cp,is3D)
            if dist>maxdistance:
                maxdistance=dist
                farthest = cp
    print("FARTHEST:", farthest)
    if farthest is not None:
        return LiteralUtils.processGeomToLiteral(farthest,a.datatype,"")


## Flips the XY coordinates included in the given geometry
#  @param a The geometry literal
#  @returns The geometry with XY flipped as a geometry literal of the same type and CRS as the input geometry
def flipXY(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.ops.transform(lambda x, y: (y, x),thegeom), a.datatype, thegeomsrs)

## Removes Z coordinates from the given geometry to make it twodimensional
#  @param a The geometry literal
#  @returns The geometry with Z coordinate removed as a geometry literal of the same type and CRS as the input geometry
def force2D(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.force_2d(thegeom), a.datatype, thegeomsrs)

def force3D(a: Literal,zval: Literal) -> Literal:
    return extrude(a,zval)

## Sets a clockwise ring orientation on the exterior ring of a polygon. Interior rings will be set to a counterclockwise orientation.
#  @param a The geometry literal
#  @returns The oriented polygon as a geometry literal in the CRS and literal format of the first input geometry
def forceCW(a: Literal) -> Literal:
    thegeom, thegeomsrs = a.value
    return Literal(shapely.orient_polygons(thegeom,exterior_cw=False), datatype=XSD.boolean)

## Sets a counterclockwise ring orientation on the exterior ring of a polygon. Interior rings will be set to a clockwise orientation.
#  @param a The geometry literal
#  @returns The oriented polygon as a geometry literal in the CRS and literal format of the first input geometry
def forceCCW(a: Literal) -> Literal:
    thegeom, thegeomsrs = a.value
    return Literal(shapely.orient_polygons(thegeom,exterior_cw=True), datatype=XSD.boolean)

## Calculates the FrechetDistance between two input geometries.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The frechet distance as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def frechetDistance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.frechet_distance(geoms[0], geoms[1]), datatype=XSD.double)

def fullyWithinDistance(a: Literal, b: Literal, distance: Literal) -> Literal:
    if isinstance(distance, Literal) and distance.datatype == XSD.double:
        geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
        is3D = Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1])
        g1list = shapely.get_coordinates(geoms[0], include_z=is3D).tolist()
        g2list = shapely.get_coordinates(geoms[1], include_z=is3D).tolist()
        thedistance=float(distance)
        maxdistance=float("-inf")
        for p1 in g1list:
            for p2 in g2list:
                dist=Handling3D.distanceWrapper(shapely.geometry.Point(p1),shapely.geometry.Point(p2),is3D)
                if dist>maxdistance:
                    maxdistance=dist
        return Literal(maxdistance<=thedistance,datatype=XSD.boolean)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/geometryN">geof:geometryN</a>: Returns the nth geometry of a GeometryCollection if it exists
#  @param a The geometry literal
#  @param n The index of the GeometryCollection to retrieve
#  @returns The geometry at the nth position of the given GeometryColleciton as a geometry literal of the same type and CRS as the input geometry
def geometryN(a: Literal, n: Literal) -> Literal:
    if isinstance(a, Literal) and isinstance(n, Literal) and n.datatype == XSD.integer:
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        return LiteralUtils.processGeomToLiteral(shapely.get_geometry(thegeom, int(str(n))), a.datatype, thegeomsrs)

def geometricMedian(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    #print("MEDIAN: "+str(Handling3D.geometricMedian(thegeom),))
    return LiteralUtils.processGeomToLiteral(Handling3D.geometricMedian(thegeom), a.datatype, thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/geometryType">geof:geometryType</a>: Retrieves the geometry type of a geometry literal.
#  @param a The geometry literal
#  @returns The geometry type as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#string">xsd:string</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def geometryType(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.geom_type, datatype=XSD.string)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/getSRID">geof:getSRID</a>: Retrieves the SRID URI of a geometry.
#  @param a The geometry literal
#  @returns The srid URI as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#anyURI">xsd:anyURI</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def getSRID(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeomsrs, datatype=XSD.anyURI)


## Calculates the HausdorffDistance between two input geometries.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The hausdorff distance as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def hausdorffDistance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.hausdorff_distance(geoms[0], geoms[1]), datatype=XSD.double)

## Calculates whether the first geometry is in front of the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is in front of the second geometry
def inFrontOf(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None and Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
        #geom[0].minZ>geom[1].maxZ
        geom1bounds=shapely.total_bounds(geoms[0])
        geom2bounds = shapely.total_bounds(geoms[1])
        rox=range_overlap(geom1bounds[0],geom1bounds[2],geom2bounds[0],geom2bounds[2])
        roy=range_overlap(geom1bounds[1],geom1bounds[3],geom2bounds[1],geom2bounds[3])
        geom1minZ=Handling3D.minZ(geoms[0])
        geom2maxZ=Handling3D.maxZ(geoms[1])
        return Literal(rox>0 and roy>0 and geom1minZ>geom2maxZ, datatype=XSD.boolean)
    raise ValueError("At least one of the input geometries are not valid or not in 3D")

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehInside">geof:ehInside</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8ntpp">geof:rcc8ntpp</a>: Calculates whether the first geometry is inside the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is inside the second geometry
def inside(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        print(shapely.contains_properly(geoms[1], geoms[0]))
        return Literal(shapely.contains_properly(geoms[1], geoms[0]), datatype=XSD.boolean)

## Returns a point interpolated at a given distance on a line.
#  @param a The geometry literal
#  @param d The distance
#  @returns The interpolated point
def interpolatePoint(a: Literal, d: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print(thegeom)
    print(d.value)
    return LiteralUtils.processGeomToLiteral(shapely.line_interpolate_point(thegeom,float(str(d.value))), a.datatype)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/intersection">geof:intersection</a>: Calculates the intersection of two geometry literals.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The intersection as a geometry literal in the CRS and literal format of the first input geometry
def intersection(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.intersection(geomtps[0][0], geomtps[1][0]), a.datatype,geomtps[0][1])


def intersection3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, create3D=True)))[0]
    print(geoms)
    print(geoms[0].intersection(geoms[1]))
    print(geoms[0].intersection(geoms[1]).volume)
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(str(geoms[0].intersection(geoms[1])), datatype=XSD.string)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfIntersects">geof:sfIntersects</a>: Calculates whether the two input geometries intersect.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the two geometries intersect
def intersects(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.intersects(geoms[0], geoms[1]), datatype=XSD.boolean)


def intersects3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, create3D=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        print(trimesh.boolean.boolean_manifold(geoms, "intersection"))
        return Literal(trimesh.boolean.boolean_manifold(geoms, "intersection").volume>0, datatype=XSD.boolean)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/is3D">geof:is3D</a>: Calculates whether a geometry literal represents a 3D geometry.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is threedimensional
def is3D(a: Literal) -> Literal:
    thegeom, thegeomsrs = a.value
    return Literal(thegeom.has_z, datatype=XSD.boolean)

## Checks whether the coordinates of a LineString or LinearRing are counterclockwise.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the LineString or LinearRing is counterclockwise
def isCCW(a: Literal) -> Literal:
    thegeom, thegeomsrs = a.value
    return Literal(shapely.is_ccw(thegeom), datatype=XSD.boolean)

## Indicates whether a geometry literal contains a GeometryCollection.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is a GeometryCollection
def isCollection(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(str(thegeom.geom_type) == "GeometryCollection" or str(thegeom.geom_type).startswith("Multi"),
                   datatype=XSD.boolean)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/isClosed">geof:isClosed</a>: Calculates whether a geometry literal represents a closed geometry.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is closed
def isClosed(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if "Polygon" in thegeom.geom_type:
        return Literal(True, datatype=XSD.boolean)
    return Literal(thegeom.is_closed, datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/isEmpty">geof:isEmpty</a>: Calculates whether a geometry literal represents a closed geometry.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is closed
def isEmpty(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.is_empty(thegeom), datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/isMeasured">geof:isMeasured</a>: Calculates whether a geometry literal has measurement coordinates.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry has measurement coordinates
def isMeasured(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.has_m, datatype=XSD.boolean)

## Calculates whether a geometry literal represents a rectangle.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is a rectangle
def isRectangle(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if "Polygon" in str(thegeom.geom_type):
        return Literal(math.isclose(thegeom.minimum_rotated_rectangle.area, thegeom.area),datatype=XSD.boolean)
    return Literal(False, datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/isRing">geof:isRing</a>: Calculates whether a geometry literal is a ring.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is a ring
def isRing(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if "Polygon" in str(thegeom.geom_type):
        return Literal(True, datatype=XSD.boolean)
    return Literal(thegeom.is_ring, datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/isSimple">geof:isSimple</a>: Calculates whether a geometry literal represents a simple geometry.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is simple
def isSimple(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.is_simple, datatype=XSD.boolean)

## Calculates whether a geometry is a triangle.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> whether the geometry is a triangle
def isTriangle(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom.geom_type=="Triangle" or (thegeom.geom_type=="Polygon" and shapely.count_coordinates(thegeom)==4):
        return Literal(True, datatype=XSD.boolean)
    return Literal(False, datatype=XSD.boolean)

## Calculates whether a geometry literal represents a valid geometry.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is valid
def isValid(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.is_valid, datatype=XSD.boolean)

## Calculates whether a geometry literal encodes a valid trajectory.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry encodes a valid trajectory
def isValidTrajectory(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom.geom_type=="LineString" and shapely.has_m(thegeom):
        clist = shapely.get_coordinates(thegeom, include_m=True).tolist()
        curM=-float("inf")
        print(clist)
        for c in clist:
            print("curM: " + str(curM))
            if curM>c[2]:
                return Literal(False, datatype=XSD.boolean)
            curM = c[2]
        return Literal(True, datatype=XSD.boolean)
    return Literal(False, datatype=XSD.boolean)

## Calculates whether the first geometry is left of the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is left of the second geometry
def leftOf(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        if Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
            geom1bounds = shapely.total_bounds(geoms[0])
            geom2bounds = shapely.total_bounds(geoms[1])
            roy = range_overlap(geom1bounds[1], geom1bounds[3], geom2bounds[1], geom2bounds[3])
            roz = range_overlap(Handling3D.minZ(geoms[0]), Handling3D.maxZ(geoms[0]), Handling3D.minZ(geoms[1]),
                                Handling3D.maxZ(geoms[1]))
            return Literal(
                roy > 0 and roz > 0 and shapely.total_bounds(geoms[0])[2] < shapely.total_bounds(geoms[1])[0],
                datatype=XSD.boolean)
        else:
            geom1bounds=shapely.total_bounds(geoms[0])
            geom2bounds=shapely.total_bounds(geoms[1])
            ro=range_overlap(geom1bounds[1],geom1bounds[3],geom2bounds[1],geom2bounds[3])
            return Literal(ro>0 and geom1bounds[2]<geom2bounds[0], datatype=XSD.boolean)
    raise ValueError("One of the input geometries is not valid")

## Calculates whether the first 3D geometry is left of the 3D second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first 3D geometry is left of the second 3D geometry
def leftOf3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None and Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
        #geom[0].maxX<geom[1].minX
        geom1bounds=shapely.total_bounds(geoms[0])
        geom2bounds=shapely.total_bounds(geoms[1])
        roy=range_overlap(geom1bounds[1],geom1bounds[3],geom2bounds[1],geom2bounds[3])
        roz=range_overlap(Handling3D.minZ(geoms[0]),Handling3D.maxZ(geoms[0]),Handling3D.minZ(geoms[1]),Handling3D.maxZ(geoms[1]))
        return Literal(roy>0 and roz>0 and shapely.total_bounds(geoms[0])[2]<shapely.total_bounds(geoms[1])[0], datatype=XSD.boolean)
    raise ValueError("At least one of the input geometries is not valid or not 3D")

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/length">geof:length</a>: Retrieves the length of a geometry.
#  @param a The geometry literal
#  @param units The unit of measurement of the length as a URI
#  @returns The length as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def length(a: Literal,unit: Literal) -> Literal:
    if unit.value not in SRSUtils.uniturisToUnit:
        raise ValueError("The provided unit "+str(unit)+" is not a supported unit.\nSupported units: "+str(SRSUtils.uniturisToUnit.keys()))
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    if thegeom.has_z:
        thelength=Handling3D.length3D(shapely.get_coordinates(normgeom, include_z=True))
    else:
        thelength=normgeom.length
    if SRSUtils.uniturisToUnit[unit.value]!="meter":
        thelength=SRSUtils.convertMetricToUnit(thelength,"http://qudt.org/vocab/unit/M",unit.value)
    return Literal(thelength, datatype=XSD.double)

## Retrieves the longest line between two geometries defined by the two points with maximum distance
#  @param a The first geometry literal.
#  @param b The first geometry literal.
#  @returns The longest line as a geometry literal in the CRS and literal format of the first input geometry
def longestLine(a: Literal, b: Literal) -> Literal:
    print("LONGESTLINE")
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    is3D=Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1])
    g1list = shapely.get_coordinates(geoms[0], include_z=is3D).tolist()
    g2list = shapely.get_coordinates(geoms[1], include_z=is3D).tolist()
    maxdistance=float("-inf")
    fpoint1=None
    fpoint2=None
    for p1 in g1list:
        p1p=shapely.geometry.Point(p1)
        for p2 in g2list:
            dist = Handling3D.distanceWrapper(p1p, shapely.geometry.Point(p2),is3D)
            #print(dist)
            if dist>maxdistance:
                maxdistance=dist
                fpoint1=p1
                fpoint2=p2
    if fpoint1 is not None and fpoint2 is not None:
        return LiteralUtils.processGeomToLiteral(shapely.geometry.LineString([fpoint1,fpoint2]),a.datatype)

## Retrieves the M coordinate of a Point geometry.
#  @param a The geometry literal.
#  @returns The M coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def m(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom.geom_type == "Point":
        return Literal(shapely.get_m(thegeom), datatype=XSD.double)

## Creates a valid version of an invalid geometry.
#  @param a The geometry literal
#  @returns A valid version of the given input geometry in the CRS and literal format of the first input geometry
def makeValid(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.make_valid(thegeom), a.datatype)


def maximumInscribedCircle(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    circdata=shapely.maximum_inscribed_circle(thegeom)
    thecircle=shapely.Point(shapely.get_coordinates(circdata)[0]).buffer(circdata.length)
    return LiteralUtils.processGeomToLiteral(thecircle, a.datatype)

## Retrieves the maximum distance between two geometries
#  @param a The first geometry literal.
#  @param b The first geometry literal.
#  @returns The maximum distance as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def maxDistance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    is3D=Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1])
    g1list = shapely.get_coordinates(geoms[0], include_z=is3D).tolist()
    g2list = shapely.get_coordinates(geoms[1], include_z=is3D).tolist()
    maxdistance=float("-inf")
    for p1 in g1list:
        p1p=shapely.geometry.Point(p1)
        for p2 in g2list:
            dist=Handling3D.distanceWrapper(p1p,shapely.geometry.Point(p2),is3D)
            if dist>maxdistance:
                maxdistance=dist
    return Literal(str(maxdistance), datatype=XSD.double)

## Retrieves the maximum measurement coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The maximum measurement coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def maxM(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    clist = shapely.get_coordinates(thegeom, include_m=True).tolist()
    flinf = -float("inf")
    maxM = flinf
    for c in clist:
        if c[2] != math.nan and maxM < c[2]:
            maxM = c[2]
    if maxM == flinf:
        maxM = "NaN"
    return Literal(str(maxM), datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/maxX">geof:maxX</a>: Retrieves the maximum x coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The maximum X coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def maxX(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.total_bounds(thegeom)[2], datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/maxY">geof:maxY</a>: Retrieves the maximum y coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The maximum Y coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def maxY(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.total_bounds(thegeom)[3], datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/maxZ">geof:maxZ</a>: Retrieves the maximum z coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The maximum Z coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def maxZ(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(str(Handling3D.maxZ(thegeom)), datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/metricArea">geof:metricArea</a>: Calculates the area of a 2D geometry provided as a geometry literal in squaremeters.
#  @param a The geometry literal.
#  @returns The area in squaremeters as an <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def metricArea(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    return Literal(shapely.area(normgeom), datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/metricBuffer">geof:metricBuffer</a>: Calculates a buffer of a 2D geometry from a given radius.
#  @param a The geometry literal.
#  @param radius The radius of the buffer to create.
#  @returns The buffer as a geometry <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def metricBuffer(a: Literal, radius: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    if isinstance(radius, Literal) and radius.datatype == XSD.double:
        return LiteralUtils.processGeomToLiteral(shapely.buffer(normgeom, float(radius)), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/metricDistance">geof:metricDistance</a>: Retrieves the distance between two geometries in meters.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The distance in meters as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def metricDistance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, normsrs=3857)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.distance(geoms[0], geoms[1]), datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/metricLength">geof:metricLength</a>: Retrieves the length of a geometry in meters.
#  @param a The geometry literal
#  @returns The length in meters as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def metricLength(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    return Literal(shapely.length(normgeom), datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/metricPerimeter">geof:metricPerimeter</a>: Retrieves the perimeter length of a geometry in meters.
#  @param a The geometry literal
#  @returns The perimeter length in meters as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def metricPerimeter(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    return Literal(normgeom.length, datatype=XSD.double)

## Calculates whether the first geometry is within a given distance to the second geometry. The distance is interpreted as meters.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @param d The distance in meters
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is within distance of the second geometry
def metricWithinDistance(a: Literal, b, d) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, normsrs=3857)))[0]
    if isinstance(d, Literal) and d.datatype == XSD.double:
        distance = float(str(d))
        return Literal(shapely.dwithin(geoms[0], geoms[1], distance), datatype=XSD.boolean)

## Calculates the radius of the minimum bounding circle around the input geometry.
#  @param a The geometry literal.
#  @returns The minimum bounding radius as <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def minimumBoundingRadius(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.minimum_bounding_radius(thegeom), datatype=XSD.double)

## Calculates the minimum clearance of the input geometry.
#  @param a The geometry literal.
#  @returns The minimum clearance as <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def minimumClearance(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.minimum_clearance(thegeom), datatype=XSD.double)

## Retrieves the minimum clearance line of a geometry
#  @param a The first geometry literal.
#  @returns The minimum clearance line as a geometry literal in the CRS and literal format of the first input geometry
def minimumClearanceLine(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    # print(shapely.minimum_clearance_line(thegeom))
    return LiteralUtils.processGeomToLiteral(shapely.minimum_clearance_line(thegeom), a.datatype)

## Retrieves the minimum measurement coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The minimum measurement coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def minM(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    clist = shapely.get_coordinates(thegeom, include_m=True).tolist()
    flinf = float("inf")
    minM = flinf
    for c in clist:
        if c[2] != math.nan and minM > c[2]:
            minM = c[2]
    if minM == flinf:
        minM = "NaN"
    return Literal(str(minM), datatype=XSD.double)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/minX">geof:minX</a>: Retrieves the minimum X coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The minimum X coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def minX(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.total_bounds(thegeom)[0], datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/minY">geof:minY</a>: Retrieves the minimum Y coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The minimum Y coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def minY(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.total_bounds(thegeom)[1], datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/minZ">geof:minZ</a>: Retrieves the minimum z coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The minimum z coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def minZ(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(str(Handling3D.minZ(thegeom)), datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/numGeometries">geof:numGeometries</a>: Calculates the number of geometries included in the geometry literal.
#  @param a The first geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#integer">xsd:integer</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating the number of geometries included
def numGeometries(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.get_num_geometries(thegeom), datatype=XSD.integer)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/numInteriorRing">geof:numInteriorRing</a>: Calculates the number of interior rings included in the geometry literal.
#  @param a The first geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#integer">xsd:integer</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating the number of interior rings
def numInteriorRing(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.get_num_interior_rings(thegeom), datatype=XSD.integer)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/numPatches">geof:numPatches</a>: Calculates the number of patches included in the geometry literal.
#  @param a The first geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#integer">xsd:integer</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating the number of patches
def numPatches(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(len(shapely.get_parts(thegeom)), datatype=XSD.integer)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/numPoints">geof:numPoints</a>: Calculates the number of points included in the geometry literal.
#  @param a The first geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#integer">xsd:integer</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating the number of points
def numPoints(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.count_coordinates(thegeom), datatype=XSD.integer)

## Creates an offset line at a given distance and side from an input geometry .
#  @param a The geometry literal
#  @param d The distance
#  @returns The offset curve as a LineString in the CRS and literal format of the input geometry
def offsetCurve(a: Literal,d: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.offset_curve(thegeom,float(str(d))), a.datatype)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfOverlaps">geof:sfOverlaps</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehOverlap">geof:ehOverlap</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8po">geof:rcc8po</a>: Calculates whether the two input geometries overlap.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the two geometries overlap
def overlaps(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.overlaps(geoms[0], geoms[1]), datatype=XSD.boolean)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/patchN">geof:patchN</a>: Returns the nth patch of a geometry
#  @param a The geometry literal
#  @param n The index of the patch to retrieve
#  @returns The point at the nth patch of the given geometry as a geometry literal of the same type and CRS as the input geometry
def patchN(a: Literal, n: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.get_parts(thegeom).tolist()[n], a.datatype)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/pointN">geof:pointN</a>: Returns the nth point of a geometry
#  @param a The geometry literal
#  @param n The index of the point to retrieve
#  @returns The point at the nth position of the given geometry as a geometry literal of the same type and CRS as the input geometry
def pointN(a: Literal, n) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if "Polygon" in str(thegeom.geom_type):
        return LiteralUtils.processGeomToLiteral(shapely.get_point(shapely.get_exterior_ring(thegeom), int(str(n))), a.datatype, thegeomsrs)
    return LiteralUtils.processGeomToLiteral(shapely.get_point(thegeom, int(str(n))), a.datatype, thegeomsrs)


## Checks if a point is include inside a circle. If the inputs are 3D geometries, checks if the input is contained in a sphere.
#  @param a The geometry literal
#  @param center The point geometry of the center of the circle
#  @param radius The radius of the circle
#  @returns True if the point is included in the sphere, false otherwise
def pointInsideCircle(a: Literal, centerpoint:Literal, rad) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    cpoint, centersrs = LiteralUtils.processLiteralTypeToGeom(centerpoint)
    if shapely.has_z(thegeom) and shapely.has_z(cpoint):
        return Literal(((shapely.get_x(thegeom) - shapely.get_x(cpoint)) ** 2 + (shapely.get_y(thegeom) - shapely.get_y(cpoint)) ** 2 + (shapely.get_z(thegeom) - shapely.get_z(cpoint)) ** 2 <= rad ** 2), datatype=XSD.boolean)
    return Literal(((shapely.get_x(thegeom) - shapely.get_x(cpoint)) ** 2 + (shapely.get_y(thegeom) - shapely.get_y(cpoint)) ** 2 <= rad ** 2), datatype=XSD.boolean)

## Returns a point on the surface of the given geometry
#  @param a The geometry literal
#  @returns The surface point as a geometry literal of the same type and CRS as the input geometry
def pointOnSurface(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print(shapely.point_on_surface(thegeom))
    return LiteralUtils.processGeomToLiteral(shapely.point_on_surface(thegeom), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/perimeter">geof:perimeter</a>: Retrieves the perimeter length of a geometry.
#  @param a The geometry literal
#  @param units The unit of measurement of the length as a URI
#  @returns The perimeter length as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def perimeter(a: Literal, unit: Literal) -> Literal:
    if unit.value not in SRSUtils.uniturisToUnit:
        raise ValueError("The provided unit "+str(unit)+" is not a supported unit.\nSupported units: "+str(SRSUtils.uniturisToUnit.keys()))
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    theperimeter=normgeom.length
    if SRSUtils.uniturisToUnit[unit.value]!="meter":
        theperimeter=SRSUtils.convertMetricToUnit(theperimeter,"http://qudt.org/vocab/unit/M",unit.value)
    return Literal(theperimeter, datatype=XSD.double)


def reducePrecision(a: Literal, gridsize: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.set_precision(thegeom,float(gridsize.value)), a.datatype)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/relate">geof:relate</a>: Calculates whether two input geometries conform to a given DE-9IM pattern.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @param matrix The DE-9IM pattern
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the two geometries conform with the DE-9IM pattern
def relate(a: Literal, b: Literal, matrix: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.relate_pattern(geoms[0], geoms[1], str(matrix)), datatype=XSD.boolean)

## Removes the coordinate at the givein index from the
#  @param a The geometry literal
#  @returns The geometry without repeated points in the CRS and literal format of the input geometry
def removePoint(a: Literal, pointIndex: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    theindex=int(pointIndex.value)
    if thegeom.geom_type == "Point":
        if theindex==0:
            return LiteralUtils.processGeomToLiteral(shapely.geometry.Point(), a.datatype)
        raise ValueError("Selected to remove a coordinate from a Point geometry with index greater 0")
    if thegeom.geom_type == "LineString":
        coords=list(thegeom.coords)
        if theindex<len(coords):
            coords.pop(theindex)
        return LiteralUtils.processGeomToLiteral(shapely.geometry.LineString(coords), a.datatype)
    if thegeom.geom_type == "Polygon":
        coords = list(thegeom.exterior.coords)
        if theindex<len(coords):
            coords.pop(theindex)
        if coords[0] != coords[-1]:
            coords[-1] = coords[0]
        return LiteralUtils.processGeomToLiteral(shapely.geometry.Polygon(coords), a.datatype)
    raise ValueError("This function is only support for Point, LineString and Polygon geometries")

## Creates a geometry without repeated points.
#  @param a The geometry literal
#  @returns The geometry without repeated points in the CRS and literal format of the input geometry
def removeRepeatedPoints(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.remove_repeated_points(thegeom), a.datatype)

## Returns a version of the input geometry with reversed point order.
#  @param a The geometry literal
#  @returns The reversed geometry in the same literal format and CRS as the input geometry
def reverse(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.reverse(thegeom), a.datatype, thegeomsrs)

## Calculates whether the first geometry is right of the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is right of the second geometry
def rightOf(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        if Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
            # geom[0].minX>geom[1].maxX
            geom1bounds = shapely.total_bounds(geoms[0])
            geom2bounds = shapely.total_bounds(geoms[1])
            roy = range_overlap(geom1bounds[1], geom1bounds[3], geom2bounds[1], geom2bounds[3])
            roz = range_overlap(Handling3D.minZ(geoms[0]), Handling3D.maxZ(geoms[0]), Handling3D.minZ(geoms[1]),
                                Handling3D.maxZ(geoms[1]))
            return Literal(
                roy > 0 and roz > 0 and shapely.total_bounds(geoms[0])[0] > shapely.total_bounds(geoms[1])[2],
                datatype=XSD.boolean)
        else:
            #geom[0].minX>geom[1].maxX
            geom1bounds=shapely.total_bounds(geoms[0])
            geom2bounds=shapely.total_bounds(geoms[1])
            ro=range_overlap(geom1bounds[1],geom1bounds[3],geom2bounds[1],geom2bounds[3])
            return Literal(ro>0 and shapely.total_bounds(geoms[0])[0]>shapely.total_bounds(geoms[1])[2], datatype=XSD.boolean)
    raise ValueError("At least one of the given input geometries is not valid")

## Calculates whether the first 3D geometry is right of the second 3D geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first 3D geometry is right of the second 3D geometry
def rightOf3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None and Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
        #geom[0].minX>geom[1].maxX
        geom1bounds=shapely.total_bounds(geoms[0])
        geom2bounds=shapely.total_bounds(geoms[1])
        roy=range_overlap(geom1bounds[1],geom1bounds[3],geom2bounds[1],geom2bounds[3])
        roz=range_overlap(Handling3D.minZ(geoms[0]),Handling3D.maxZ(geoms[0]),Handling3D.minZ(geoms[1]),Handling3D.maxZ(geoms[1]))
        return Literal(roy>0 and roz>0 and shapely.total_bounds(geoms[0])[0]>shapely.total_bounds(geoms[1])[2], datatype=XSD.boolean)
    raise ValueError("At least one of the given input geometries is not valid or not in 3D")


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/relate">geof:relate</a>: Calculates whether two input geometries conform to a given DE-9IM pattern.
#  @param a The first geometry literal
#  @param b The rotation angle in degree
#  @returns A rotated geometry
def rotate(a: Literal,angle: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.affinity.rotate(thegeom,float(angle.value)), datatype=XSD.boolean)

## Returns a scaled version of the input geometry.
#  @param a The geometry literal
#  @param scaleX The scale factor in X direction
#  @param scaleY The scale factor in Y direction
#  @param scaleZ The scale factor in Z direction
#  @returns The scaled geometry in the same literal format and CRS as the input geometry
def scale(a: Literal, scaleX: Literal, scaleY: Literal, scaleZ: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print(shapely.affinity.scale(thegeom, xfact=float(scaleX.value), yfact=float(scaleY.value),
                                 zfact=float(scaleZ.value)))
    return LiteralUtils.processGeomToLiteral(
        shapely.affinity.scale(thegeom, xfact=float(scaleX.value), yfact=float(scaleY.value),
                               zfact=float(scaleZ.value)), a.datatype, thegeomsrs)

## Sets the coordinate at the given index with the given point
#  @param a The geometry literal
#  @param b The coordinate to replace
#  @returns The geometry with the replace coordiante in the CRS and literal format of the input geometry
def setPoint(a: Literal, b:Literal, pointindex: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    theindex=int(pointindex.value)
    if geoms[1].geom_type == "Point":
        if geoms[0].geom_type == "Point":
            if theindex==0:
                coords = list(geoms[0].coords)
                coords[theindex]=geoms[1].coords[0]
                return LiteralUtils.processGeomToLiteral(shapely.geometry.LineString(coords), a.datatype)
            raise ValueError("Selected to remove a coordinate from a Point geometry with index greater 0")
        if geoms[0].geom_type == "LineString":
            coords=list(geoms[0].coords)
            coords[theindex]=geoms[1].coords[0]
            return LiteralUtils.processGeomToLiteral(shapely.geometry.LineString(coords), a.datatype)
        if geoms[0].geom_type == "Polygon":
            coords = list(geoms[0].exterior.coords)
            coords[theindex]=geoms[1].coords[0]
            if coords[0] != coords[-1]:
                coords[-1] = coords[0]
            return LiteralUtils.processGeomToLiteral(shapely.geometry.Polygon(coords), a.datatype)
    raise ValueError("This function is only support for Point, LineString and Polygon geometries")

def sharedPaths(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.shared_paths(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])

## Retrieves the shortest line between two geometries defined by the two points with minimum distance
#  @param a The first geometry literal.
#  @param b The first geometry literal.
#  @returns The shortest line as a geometry literal in the CRS and literal format of the first input geometry
def shortestLine(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.shortest_line(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])

## Returns a simplfied version of the input geometry calculated with the Douglas Peucker simplification algoritm.
#  @param a The geometry literal
#  @param tolerance a tolerance value
#  @returns The simplified geometry in the same literal format and CRS as the input geometry
def simplify(a: Literal, tolerance: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.simplify(thegeom, float(tolerance)), a.datatype, thegeomsrs)

## Returns a skewed version of the input geometry.
#  @param a The geometry literal
#  @param xs The skew value in X direction
#  @param xy The skew value in Y direction
#  @returns The skewed geometry in the same literal format and CRS as the input geometry
def skew(a: Literal, xs: Literal, ys: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.affinity.skew(thegeom, xs, ys), a.datatype, thegeomsrs)

def smooth(a: Literal, tolerance: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapelysmooth.chaikin_smooth(thegeom), a.datatype, thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/spatialDimension">geof:spatialDimension</a>: Calculates the spatial dimension of a geometry literal.
#  @param a The geometry literal
#  @returns The spatial dimension as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#integer">xsd:integer</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def spatialDimension(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.get_dimensions(thegeom), datatype=XSD.integer)


def selfIntersections(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    unioned=shapely.ops.unary_union(thegeom)
    print(unioned)
    coordsres=[]
    print(coordsres)
    for intp in unioned:
        print(intp)
        coordsres.append(intp.coords)
    print([item for item, count in collections.Counter(coordsres).items() if count > 1])


## Extracts the first point of an input geometry.
#  @param a The geometry literal
#  @returns The first point as a geometry literal in the CRS and literal format of the input geometry
def startPoint(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.Point(shapely.get_coordinates(thegeom)[0]), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/symDifference">geof:symDifference</a>: Calculates the symmetric difference of two geometry literals.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The symmetric difference as a geometry literal in the CRS and literal format of the first input geometry
def symDifference(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.symmetric_difference(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/transform">geof:transform</a>: Transforms a given geometry literal to a given CRS.
#  @param a The geometry literal
#  @param srsIRI The IRI identifying the target CRS
#  @returns The transformed geometry as a geometry literal in the same literal format as the input geometry
def transform(a: Literal, srsIRI: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print("TRANSFORM FUNCTION")
    geom=Transformers.transformToSRS(thegeom, thegeomsrs, srsIRI)
    print("GEOM: "+str(geom))
    print("AS LITERAL: "+str(LiteralUtils.processGeomToLiteral(geom, a.datatype,srsIRI)))
    if thegeom is not None and thegeomsrs is not None:
        return LiteralUtils.processGeomToLiteral(Transformers.transformToSRS(thegeom, thegeomsrs, srsIRI), a.datatype,srsIRI)
    raise ValueError("An invalid geometry literal was provided or an illegal transformation requested for function geof:transform")

## Transforms a given geometry literal to the CRS84 CRS.
#  @param a The geometry literal
#  @returns The transformed geometry as a geometry literal in the same literal format as the input geometry
def transformCRS84(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom is not None and thegeomsrs is not None:
        return LiteralUtils.processGeomToLiteral(Transformers.transformToSRS(thegeom, thegeomsrs, CRS84URI), a.datatype,
                                                 CRS84URI)
    raise ValueError(
        "An invalid geometry literal was provided or an illegal transformation requested for function geof:transformCRS84")

## Returns a translated version of the input geometry.
#  @param a The geometry literal
#  @param deltaX The translation value in X direction
#  @param deltaY The translation value in Y direction
#  @param deltaZ The translation value in Z direction
#  @returns The translated geometry in the same literal format and CRS as the input geometry
def translate(a: Literal, deltaX: Literal, deltaY: Literal, deltaZ: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if (isinstance(deltaX, Literal) and deltaX.datatype == XSD.double and isinstance(deltaY,
                                                                                     Literal) and deltaY.datatype == XSD.double and isinstance(
            deltaZ, Literal) and deltaZ.datatype == XSD.double):
        return LiteralUtils.processGeomToLiteral(
            shapely.affinity.translate(thegeom, float(deltaX.value), float(deltaY.value), float(deltaZ.value)),
            a.datatype, thegeomsrs)
    raise ValueError("Invalid parameters were provided for function geof:translate")


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfTouches">geof:sfTouches</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/ehMeet">geof:ehMeet</a> <a target="_blank" href="http://www.opengis.net/def/function/geosparql/rcc8ec">geof:rcc8ec</a>: Calculates whether the two input geometries touch.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the two geometries touch
def touches(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.touches(geoms[0], geoms[1]), datatype=XSD.boolean)
    raise ValueError("Invalid parameters were provided for function geof:touches")


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/union">geof:union</a>: Calculates the union of two geometry literals.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The union as a geometry literal in the CRS and literal format of the first input geometry
def union(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.union(geomtps[0][0], geomtps[1][0]), a.datatype, geomtps[0][1])
    raise ValueError("Invalid parameters were provided for function geof:union")


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/union">geof:union</a>: Calculates the union of two geometry literals.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns The union as a geometry literal in the CRS and literal format of the first input geometry
def union3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, create3D=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        print(trimesh.boolean.boolean_manifold(geoms, "intersection"))
        return Literal(trimesh.boolean.union(geoms), datatype=XSD.boolean)

def voronoiLines(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom is not None:
        return LiteralUtils.processGeomToLiteral(shapely.voronoi_polygons(thegeom, only_edges=True),a.datatype)

def voronoiPolygons(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom is not None:
        return LiteralUtils.processGeomToLiteral(shapely.voronoi_polygons(thegeom),a.datatype)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/sfWithin">geof:sfWithin</a>: Calculates whether the first geometry is within the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is within the second geometry
def within(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.within(geoms[0], geoms[1]), datatype=XSD.boolean)
    raise ValueError("Invalid parameters were provided for function geof:within")

## Calculates whether the first geometry is within a given distance to the second geometry.
#  @param a The first geometry literal
#  @param b The second geometry literal
#  @param d The distance
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the first geometry is within distance of the second geometry
def withinDistance(a: Literal, b: Literal, d: Literal, unit: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if isinstance(d, Literal) and d.datatype == XSD.double:
        distance = float(str(d))
        if Handling3D.is3D(geoms[0]) and Handling3D.is3D(geoms[1]):
            mindist3d=Handling3D.distance3DAware(geoms[0],geoms[1],True)
            return Literal(mindist3d<=distance,datatype=XSD.boolean)
        return Literal(str(shapely.dwithin(geoms[0], geoms[1], distance)), datatype=XSD.boolean)


## Retrieves the X coordinate of a Point geometry.
#  @param a The geometry literal.
#  @returns The X coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def x(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom.geom_type == "Point":
        return Literal(shapely.get_x(thegeom), datatype=XSD.double)
    raise ValueError("Invalid parameters, e.g. a non-Point geometry literal was provided for function geof:x")


## Retrieves the Y coordinate of a Point geometry.
#  @param a The geometry literal.
#  @returns The Y coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def y(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom.geom_type == "Point":
        return Literal(shapely.get_y(thegeom), datatype=XSD.double)
    raise ValueError("Invalid parameters, e.g. a non-Point geometry literal was provided for function geof:y")


## Retrieves the Z coordinate of a Point geometry.
#  @param a The geometry literal.
#  @returns The Z coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def z(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom.geom_type == "Point" and thegeom.has_z:
        return Literal(str(shapely.get_z(thegeom)), datatype=XSD.double)
    raise ValueError(
        "Invalid parameters, e.g. a non-Point geometry literal or a non-3D geometry was provided for function geof:z")


geosparql10 = {
    URIRef(GEOF + "boundary"): boundary,
    URIRef(GEOF + "buffer"): buffer,
    URIRef(GEOF + "convexHull"): convexHull,
    URIRef(GEOF + "difference"): difference,
    URIRef(GEOF + "distance"): distance,
    URIRef(GEOF + "ehContains"): contains,
    URIRef(GEOF + "ehCoveredBy"): coveredBy,
    URIRef(GEOF + "ehCovers"): covers,
    URIRef(GEOF + "ehDisjoint"): disjoint,
    URIRef(GEOF + "ehEquals"): equals,
    URIRef(GEOF + "ehInside"): inside,
    URIRef(GEOF + "ehMeet"): touches,
    URIRef(GEOF + "ehOverlap"): overlaps,
    URIRef(GEOF + "envelope"): envelope,
    URIRef(GEOF + "geometryType"): geometryType,
    URIRef(GEOF + "getSRID"): getSRID,
    URIRef(GEOF + "intersection"): intersection,
    URIRef(GEOF + "rcc8dc"): disjoint,
    URIRef(GEOF + "rcc8ec"): touches,
    URIRef(GEOF + "rcc8eq"): equals,
    URIRef(GEOF + "rcc8ntpp"): inside,
    URIRef(GEOF + "rcc8ntppi"): contains,
    URIRef(GEOF + "rcc8po"): overlaps,
    URIRef(GEOF + "rcc8tpp"): coveredBy,
    URIRef(GEOF + "rcc8tppi"): covers,
    URIRef(GEOF + "relate"): relate,
    URIRef(GEOF + "sfContains"): contains,
    URIRef(GEOF + "sfCrosses"): crosses,
    URIRef(GEOF + "sfDisjoint"): disjoint,
    URIRef(GEOF + "sfEquals"): equals,
    URIRef(GEOF + "sfIntersects"): intersects,
    URIRef(GEOF + "sfOverlaps"): overlaps,
    URIRef(GEOF + "sfTouches"): touches,
    URIRef(GEOF + "sfWithin"): within,
    URIRef(GEOF + "symDifference"): symDifference,
    URIRef(GEOF + "union"): union,
}

geosparql11 = {
    URIRef(GEOF + "area"): area,
    URIRef(GEOF + "asDGGS"): SerializationFunctions.asDGGS,
    URIRef(GEOF + "asGeoJSON"): SerializationFunctions.asGeoJSON,
    URIRef(GEOF + "asGML"): SerializationFunctions.asGML,
    URIRef(GEOF + "asKML"): SerializationFunctions.asKML,
    URIRef(GEOF + "asWKB"): SerializationFunctions.asWKB,
    URIRef(GEOF + "asWKT"): SerializationFunctions.asWKT,
    URIRef(GEOF + "boundingCircle"): boundingCircle,
    URIRef(GEOF + "centroid"): centroid,
    URIRef(GEOF + "concaveHull"): concaveHull,
    URIRef(GEOF + "coordinateDimension"): coordinateDimension,
    URIRef(GEOF + "geometryN"): geometryN,
    URIRef(GEOF + "is3D"): is3D,
    URIRef(GEOF + "isEmpty"): isEmpty,
    URIRef(GEOF + "isMeasured"): isMeasured,
    URIRef(GEOF + "isSimple"): isSimple,
    URIRef(GEOF + "length"): length,
    URIRef(GEOF + "maxX"): maxX,
    URIRef(GEOF + "maxY"): maxY,
    URIRef(GEOF + "maxZ"): maxZ,
    URIRef(GEOF + "metricArea"): metricArea,
    URIRef(GEOF + "metricBuffer"): metricBuffer,
    URIRef(GEOF + "metricDistance"): metricDistance,
    URIRef(GEOF + "metricLength"): metricLength,
    URIRef(GEOF + "metricPerimeter"): metricPerimeter,
    URIRef(GEOF + "minX"): minX,
    URIRef(GEOF + "minY"): minY,
    URIRef(GEOF + "minZ"): minZ,
    URIRef(GEOF + "numGeometries"): numGeometries,
    URIRef(GEOF + "numPoints"): numPoints,
    URIRef(GEOF + "perimeter"): perimeter,
    URIRef(GEOF + "spatialDimension"): spatialDimension,
    URIRef(GEOF + "transform"): transform,
}

geosparql13 = {
    URIRef(GEOFEXT + "above"): above,
    URIRef(GEOFEXT + "above3D"): above3D,
    URIRef(GEOFEXT + "addPoint"): addPoint,
    URIRef(GEOFEXT + "affineTransformation"): affineTransformation,
    URIRef(GEOFEXT + "appendPoint"): appendPoint,
    URIRef(GEOFEXT + "asGeocode"): SerializationFunctions.asGeocode,
    URIRef(GEOFEXT + "asGeoYAML"): SerializationFunctions.asGeoYAML,
    URIRef(GEOFEXT + "asGLTF"): SerializationFunctions.asGLTF,
    URIRef(GEOFEXT + "asJSONFG"): SerializationFunctions.asJSONFG,
    URIRef(GEOFEXT + "asOBJ"): SerializationFunctions.asOBJ,
    URIRef(GEOFEXT + "asPLY"): SerializationFunctions.asPLY,
    URIRef(GEOFEXT + "asSVG"): SerializationFunctions.asSVG,
    URIRef(GEOFEXT + "asWKB"): SerializationFunctions.asWKB,
    URIRef(GEOFEXT + "asXYZ"): SerializationFunctions.asXYZ,
    URIRef(GEOFEXT + "azimuth"): azimuth,
    URIRef(GEOFEXT + "below"): below,
    URIRef(GEOFEXT + "below3D"): below3D,
    URIRef(GEOFEXT + "behind"): behind,
    URIRef(GEOFEXT + "boundingDiagonal"): boundingDiagonal,
    URIRef(GEOFEXT + "compactnessRatio"): compactnessRatio,
    URIRef(GEOFEXT + "clipByRect"): clipByRect,
    URIRef(GEOFEXT + "closestPoint"): closestPoint,
    URIRef(GEOFEXT + "constrainedDelaunay"): constrainedDelaunay,
    URIRef(GEOFEXT + "delaunayTriangles"): delaunayTriangles,
    URIRef(GEOFEXT + "difference3D"): difference3D,
    URIRef(GEOFEXT + "endPoint"): endPoint,
    URIRef(GEOFEXT + "exteriorRing"): exteriorRing,
    URIRef(GEOFEXT + "farthestCoordinate"): farthestCoordinate,
    URIRef(GEOFEXT + "force2D"): force2D,
    URIRef(GEOFEXT + "force3D"): extrude,
    URIRef(GEOFEXT + "forceCW"): forceCW,
    URIRef(GEOFEXT + "forceCCW"): forceCCW,
    URIRef(GEOFEXT + "frechetDistance"): frechetDistance,
    URIRef(GEOFEXT + "fullyWithinDistance"): fullyWithinDistance,
    URIRef(GEOFEXT + "flipXY"): flipXY,
    URIRef(GEOFEXT + "geometricMedian"): geometricMedian,
    URIRef(GEOFEXT + "hausdorffDistance"): hausdorffDistance,
    URIRef(GEOFEXT + "inFrontOf"): inFrontOf,
    URIRef(GEOFEXT + "interpolatePoint"): interpolatePoint,
    URIRef(GEOFEXT + "intersection3D"): intersection3D,
    URIRef(GEOFEXT + "intersects3D"): intersects3D,
    URIRef(GEOFEXT + "isCCW"): isCCW,
    URIRef(GEOFEXT + "isCollection"): isCollection,
    URIRef(GEOFEXT + "isClosed"): isClosed,
    URIRef(GEOFEXT + "isRectangle"): isRectangle,
    URIRef(GEOFEXT + "isRing"): isRing,
    URIRef(GEOFEXT + "isTriangle"): isTriangle,
    URIRef(GEOFEXT + "isValid"): isValid,
    URIRef(GEOFEXT + "isValidTrajectory"): isValidTrajectory,
    URIRef(GEOFEXT + "leftOf"): leftOf,
    URIRef(GEOFEXT + "leftOf3D"): leftOf3D,
    URIRef(GEOFEXT + "longestLine"): longestLine,
    URIRef(GEOFEXT + "makeValid"): makeValid,
    URIRef(GEOFEXT + "maxDistance"): maxDistance,
    URIRef(GEOFEXT + "maximumInscribedCircle"): maximumInscribedCircle,
    URIRef(GEOFEXT + "maxM"): maxM,
    URIRef(GEOFEXT + "M"): m,
    URIRef(GEOFEXT + "metricWithinDistance"): metricWithinDistance,
    URIRef(GEOFEXT + "minM"): minM,
    URIRef(GEOFEXT + "minimumBoundingRadius"): minimumBoundingRadius,
    URIRef(GEOFEXT + "minimumClearance"): minimumClearance,
    URIRef(GEOFEXT + "minimumClearanceLine"): minimumClearanceLine,
    URIRef(GEOFEXT + "numGeometries"): numGeometries,
    URIRef(GEOFEXT + "numPatches"): numPatches,
    URIRef(GEOFEXT + "numInteriorRing"): numInteriorRing,
    URIRef(GEOFEXT + "numPoints"): numPoints,
    URIRef(GEOFEXT + "offsetCurve"): offsetCurve,
    URIRef(GEOFEXT + "patchN"): patchN,
    URIRef(GEOFEXT + "pointN"): pointN,
    URIRef(GEOFEXT + "pointOnSurface"): pointOnSurface,
    URIRef(GEOFEXT + "reducePrecision"): reducePrecision,
    URIRef(GEOFEXT + "removePoint"): removePoint,
    URIRef(GEOFEXT + "removeRepeatedPoints"): removeRepeatedPoints,
    URIRef(GEOFEXT + "reverse"): reverse,
    URIRef(GEOFEXT + "rightOf"): rightOf,
    URIRef(GEOFEXT + "rightOf3D"): rightOf3D,
    URIRef(GEOFEXT + "rotate"): rotate,
    URIRef(GEOFEXT + "scale"): scale,
    URIRef(GEOFEXT + "selfIntersections"): selfIntersections,
    URIRef(GEOFEXT + "setPoint"): setPoint,
    URIRef(GEOFEXT + "sharedPaths"): sharedPaths,
    URIRef(GEOFEXT + "shortestLine"): shortestLine,
    URIRef(GEOFEXT + "simplify"): simplify,
    URIRef(GEOFEXT + "skew"): skew,
    URIRef(GEOFEXT + "smooth"): smooth,
    URIRef(GEOFEXT + "startPoint"): startPoint,
    URIRef(GEOFEXT + "transformCRS84"): transformCRS84,
    URIRef(GEOFEXT + "translate"): translate,
    URIRef(GEOFEXT + "voronoiLines"): voronoiLines,
    URIRef(GEOFEXT + "voronoiPolygons"): voronoiPolygons,
    URIRef(GEOFEXT + "withinDistance"): withinDistance,
    URIRef(GEOFEXT + "X"): x,
    URIRef(GEOFEXT + "Y"): y,
    URIRef(GEOFEXT + "Z"): z,
}


def getfuncs():
    thefuncs = merge_dicts(geosparql10, geosparql11, geosparql13)
    print("")
    for uri in thefuncs:
        try:
            register_custom_function(uri, thefuncs[uri])
            print("Registered custom function", uri)
            # print(thefuncs[uri])
        except ValueError:
            pass
        except AttributeError:
            pass

    #term.bind(URIRef(str(GEO)+"wktLiteral"),shapely.Geometry,LiteralUtils.processWKTLiteral,LiteralUtils.processGeomToWKTLiteral)
    #term.bind(URIRef(str(GEO) + "gmlLiteral"), shapely.Geometry, LiteralUtils.processGMLLiteral,LiteralUtils.processGeomToGMLLiteral)
    #term.bind(URIRef(str(GEO) + "kmlLiteral"), shapely.Geometry, LiteralUtils.processKMLLiteral,LiteralUtils.processGeomToKMLLiteral)
    #term.bind(URIRef(str(GEO) + "geoJSONLiteral"), shapely.Geometry, LiteralUtils.processGeoJSONLiteral,LiteralUtils.processGeomToGeoJSONLiteral)

getfuncs()

g = Graph()
dir_path = os.path.dirname(os.path.realpath(__file__))
g.parse(dir_path + "/../tests/testdata.ttl")

result = g.query(
    """
PREFIX my: <http://example.org/ApplicationSchema#>
PREFIX geo: <"""+str(GEO)+""">
PREFIX geof: <"""+str(GEOFEXT)+""">
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?aLiteral ?dLiteral ?cPoint
WHERE {
  my:A my:hasGeometry ?aGeom .
  ?aGeom geo:asWKT ?aLiteral .
  my:D geo:hasGeometry ?dGeom .
  ?dGeom geo:asWKT ?dLiteral .
  BIND (geof:closestPoint(?aLiteral, ?dLiteral) as ?cPoint)
}
"""
)
print("THE RESULT")
print(result)
#print(len(result.bindings))
#print([{str(k): v for k, v in i.items()} for i in result.bindings])
for res in result:
    print(res)

#res=Transformers.transformToSRS(shapely.from_wkt("POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))"),CRS84URI,"http://www.opengis.net/def/crs/EPSG/0/4326")
#print(res)
"""
res=transform(Literal("POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))",datatype="http://www.opengis.net/ont/geosparql#wktLiteral"),"http://www.opengis.net/def/crs/EPSG/0/4326")
print(res)
#res=asDGGS(Literal("POLYGON Z((0 0 1,10 0 2,10 10 3,0 10 2,0 0 1),(5 5 2,7 5 3,7 7 4,5 7 3, 5 5 2))",datatype="http://www.opengis.net/ont/geosparql#wktLiteral"),"http://opengis.net/ont/geocode/OpenLocationCode")

reslit=Literal(str(res),datatype="http://www.opengis.net/ont/geosparql#geocodeLiteral")
print(res)
print(reslit)

geo=shapely.from_wkt("POLYGON Z((0 0 1,10 0 2,10 10 3,0 10 2,0 0 1),(5 5 2,7 5 3,7 7 4,5 7 3, 5 5 2))")
geo2=shapely.from_wkt("POLYGON Z((0 0 2,10 0 3,10 10 4,0 10 3,0 0 2),(5 5 2,7 5 3,8 8 4,5 7 3, 5 5 2))")
ress=trimesh.creation.triangulate_polygon(geo,include_z=True)
ress2=trimesh.creation.triangulate_polygon(geo2,include_z=True)
inter=trimesh.boolean.intersection(ress,ress2)
print(ress)
print(inter)
"""
# geo=kml.KML.from_string("<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Placemark><Polygon><outerBoundaryIs><LinearRing><coordinates>-83.6,34.1 -83.2,34.1 -83.2,34.5 -83.6,34.5 -83.6,34.1</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark></kml>")
# print("GEO")
# print(geo.features[0].geometry)
# pygml.parse("<gml:Polygon xmlns:gml=\"http://www.opengis.net/gml\" srsName=\"http://www.opengis.net/def/crs/OGC/1.3/CRS84\"><gml:exterior><gml:LinearRing><gml:posList>-83.6 34.1 -83.2 34.1 -83.2 34.5 -83.6 34.5 -83.6 34.1</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>".replace("http://www.opengis.net/def/crs/OGC/1.3/CRS84","http://www.opengis.net/def/crs/EPSG/0/4326"))
# geom = pygml.parse("""<gml:Point gml:id="ID" xmlns:gml="http://www.opengis.net/gml/3.2"><gml:pos></gml:pos></gml:Point>""")

# pygml.parse("<gml:Polygon xmlns:gml=\"http://www.opengis.net/ont/gml\" srsName=\"http://www.opengis.net/def/crs/OGC/1.3/CRS84\"><gml:exterior><gml:LinearRing><gml:posList>-83.6 34.1 -83.2 34.1 -83.2 34.5 -83.6 34.5 -83.6 34.1</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon>")
