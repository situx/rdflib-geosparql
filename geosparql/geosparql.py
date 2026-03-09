import json
import os
from io import BytesIO, TextIOWrapper
from math import nan, pi, sqrt, degrees, atan2
from typing import Any

import fastkml.geometry
import h3
import pygeohash
import pygml
import shapely
import trimesh
from fastkml import kml
from lxml import etree
from openlocationcode import openlocationcode
from pint import UnitRegistry
from pygml.v32 import encode_v32
from pyproj import CRS
from pyproj import Transformer
from rdflib import Literal, XSD, Graph, URIRef, term
from rdflib.plugins.sparql.operators import register_custom_function
from shapely.io import to_geojson

GEOF = "http://www.opengis.net/def/function/geosparql/"
GEOFEXT = "http://www.opengis.net/def/function/geosparql/ext/"
GEOFPREFIX = "geof:"
GEOFEXTPREFIX = "geofext:"
GEO = "http://www.opengis.net/ont/geosparql#"
CRS84URI = "http://www.opengis.net/def/crs/OGC/1.3/CRS84"


def merge_dicts(*dict_args):
    """
    Given any number of dictionaries, shallow copy and merge into a new dict,
    precedence goes to key-value pairs in latter dictionaries.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


class Transformers:

    supported_geocodes = {"http://opengis.net/ont/geocode/GeoURI",
                          "http://opengis.net/ont/geocode/OpenLocationCode",
                          "http://opengis.net/ont/geocode/GeoHash-36"}

    supported_dggs = {"https://h3geo.org/res/{RESOLUTION}"}

    @staticmethod
    def normalizeGeoms(geoms, tosrs=None):
        """
        Normalizes a list of geometry tuples to a common SRS
        Args:
            geoms: the list of geometry tuples
            tosrs: the target SRS if defined. If none, the SRS of the first geometry is used as the target

        Returns: A list of geometry tuples normalized to the target SRS

        """
        geomsnew = []
        if tosrs is None:
            tosrs = geoms[0][1]
        for geom in geoms:
            geomsnew.append((Transformers.transformToSRS(geom[0], geom[1], str(tosrs)), tosrs))
        return geomsnew

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
        elif geocodeuri == "http://opengis.net/ont/geocode/GeoHash-36":
            thecode = pygeohash.encode(latitude=geom.x, longitude=geom.y)
        return "<" + str(geocodeuri) + "> " + str(thecode)

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

    @staticmethod
    def geocodeToGeom(geocodestr,geocodeuri=""):
        if "<" in geocodestr and ">" in geocodestr:
            geocodeuri=geocodestr[0:geocodestr.find(">")].replace("<","").replace(">","").strip()
            geocodestr=geocodestr[geocodestr.find(">")+1:]
        tehvalue=""
        if geocodeuri in Transformers.supported_geocodes:
            if geocodeuri=="http://opengis.net/ont/geocode/GeoURI":
                spl=geocodestr.split(",")
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


class SRSUtils:

    ureg = UnitRegistry()
    units = {}
    units["m"] = "om:meter"
    units["metre"] = "om:metre"
    units["grad"] = "om:degree"
    units["degree"] = "om:degree"
    units["ft"] = "om:foot"
    units["us-ft"] = "om:usfoot"

    @staticmethod
    def getUnitsFromSRS(srsuri):
        curcrs = CRS.from_epsg(srsuri)
        unitres = []
        for ax in curcrs.coordinate_system.axis_list:
            if ax.unit_name in SRSUtils.units:
                unitres.append(SRSUtils.ureg.parse_expression(SRSUtils.units[ax.unit_name].replace("om:", "")))
        return unitres

    @staticmethod
    def getEastingFromSRS(srsuri):
        curcrs = CRS.from_epsg(srsuri)
        unitres = []
        for ax in curcrs.coordinate_system.axis_list:
            if ax.unit_name in SRSUtils.units:
                unitres.append(SRSUtils.ureg.parse_expression(SRSUtils.units[ax.unit_name].replace("om:", "")))
        return unitres


class LiteralUtils:

    @staticmethod
    def createGeometry3D(shapelygeom):
        # print("CREATE3D")
        # print(shapelygeom.geom_type)
        # ress=trimesh.creation.triangulate_polygon(shapelygeom)
        ress = trimesh.creation.extrude_polygon(shapelygeom, 3)
        # print(shapelygeom)
        # print(ress)
        return ress

    @staticmethod
    def processWKTLiteral(text):
        print(text)
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"wktLiteral")

    @staticmethod
    def processGMLLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"gmlLiteral")

    @staticmethod
    def processKMLLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"kmlLiteral")

    @staticmethod
    def processDGGSLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"dggsLiteral")

    @staticmethod
    def processGeoJSONLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"geoJSONLiteral")

    @staticmethod
    def processGLTFLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"gltfLiteral")

    @staticmethod
    def processPLYLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"plyLiteral")

    @staticmethod
    def processOBJLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"objLiteral")

    @staticmethod
    def processWKBLiteral(text):
        return LiteralUtils.processLiteralTypeToGeom(text,datatype=GEO+"wkbLiteral")

    @staticmethod
    def processLiteralTypeToGeom(literal, datatype=None,create3D=False, normsrs=None):
        if not isinstance(literal, Literal) and datatype is None:
            raise ValueError("The " + str(literal) + " is not a literal!")
        if datatype is None:
            dtype = str(literal.datatype)
        else:
            dtype = str(datatype)
        lstring = str(literal).strip()
        #print(literal)
        #print(dtype)
        print("LString: "+str(lstring))
        if str(dtype) == "http://www.opengis.net/ont/geosparql#wktLiteral":
            if lstring.startswith("<"):
                srsuri = lstring[0:lstring.find(">")].replace("<", "").replace(">", "")
                gstring = lstring[lstring.find(">") + 1:].strip()
                print("GString: "+str(gstring))
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
                    return (LiteralUtils.createGeometry3D(geo), srsuri)
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
        elif dtype == "http://www.opengis.net/ont/geosparql#wkbLiteral":
            geo = shapely.from_wkb(lstring)
            shapely.set_srid(geo, 4326)
            srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return (LiteralUtils.createGeometry3D(geo), srsuri)
            return (geo, srsuri)
        elif dtype == "http://www.opengis.net/ont/geosparql#gmlLiteral":
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
        elif dtype == "http://www.opengis.net/ont/geosparql#geoJSONLiteral":
            geo = shapely.from_geojson(lstring)
            shapely.set_srid(geo, 4326)
            srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return (LiteralUtils.createGeometry3D(geo), srsuri)
            return (geo, srsuri)
        elif dtype == "http://www.opengis.net/ont/geosparql#kmlLiteral":
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
            print(geo)
            shapely.set_srid(geo, 4326)
            srsuri = CRS84URI
            if normsrs is not None:
                geo = Transformers.transformToSRS(geo, CRS84URI, str(normsrs))
                srsuri = normsrs
            if create3D:
                return (LiteralUtils.createGeometry3D(geo), srsuri)
            return (geo, srsuri)
        elif dtype == "http://www.opengis.net/ont/geosparql#dggsLiteral":
            geo = Transformers.dggsToGeom(lstring)
            return (geo, CRS84URI)
        elif dtype == "http://www.opengis.net/ont/geosparql#plyLiteral":
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="ply")
            return (geo, CRS84URI)
        elif dtype == "http://www.opengis.net/ont/geosparql#objLiteral":
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="obj")
            return (geo, CRS84URI)
        elif dtype == "http://www.opengis.net/ont/geosparql#gltfLiteral":
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="gltf")
            return (geo, CRS84URI)
        elif dtype == "http://www.opengis.net/ont/geosparql#xyzLiteral":
            geo = trimesh.load(file_obj=trimesh.util.wrap_as_stream(lstring), file_type="xyz")
            return (geo, CRS84URI)
        else:
            thelit = str(literal)
            if len(thelit) > 100:
                thelit = thelit[0:100]
            raise ValueError(
                "The literal " + thelit + " (" + str(literal.datatype) + ") is no known geometry literal type!"
            )

    @staticmethod
    def processGeomToGeoJSONLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEO + "geoJSONLiteral",geomtup[1])

    @staticmethod
    def processGeomToGLTFLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEO + "gltfLiteral",geomtup[1])

    @staticmethod
    def processGeomToGMLLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEO + "gmlLiteral",geomtup[1])

    @staticmethod
    def processGeomToKMLLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEO + "kmlLiteral",geomtup[1])

    @staticmethod
    def processGeomToOBJLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEO + "objLiteral",geomtup[1])

    @staticmethod
    def processGeomToPLYLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEO + "plyLiteral",geomtup[1])

    @staticmethod
    def processGeomToWKBLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0], GEO + "wkbLiteral",geomtup[1])

    @staticmethod
    def processGeomToWKTLiteral(geomtup):
        return LiteralUtils.processGeomToLiteral(geomtup[0],GEO+"gmlLiteral",geomtup[1])

    @staticmethod
    def processGeomToLiteral(geom, literaltype, thegeomsrs="") -> Literal:
        ltype = str(literaltype)
        if ltype == "http://www.opengis.net/ont/geosparql#wktLiteral":
            if thegeomsrs != "":
                return Literal("<" + CRS84URI + "> " + str(geom.wkt), datatype=literaltype)
            else:
                return Literal("<" + str(thegeomsrs) + "> " + str(geom.wkt), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#geoJSONLiteral":
            return Literal(str(to_geojson(geom)), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#gmlLiteral":
            return Literal(etree.tostring(encode_v32(json.loads(to_geojson(geom)), "ID")), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#kmlLiteral":
            return Literal("<kml xmlns=\"http://www.opengis.net/kml/2.2\"><Placemark>" + str(
                fastkml.geometry.create_kml_geometry(geom)) + "</Placemark></kml>", datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#wkbLiteral":
            return Literal(str(geom.wkb_hex), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#plyLiteral":
            bio = BytesIO()
            geom.export(bio, file_type="ply", encoding='ascii')
            wrapper = TextIOWrapper(bio, encoding='utf-8')
            return Literal(wrapper.read(), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#objLiteral":
            bio = BytesIO()
            geom.export(bio, file_type="obj", encoding='ascii')
            wrapper = TextIOWrapper(bio, encoding='utf-8')
            return Literal(wrapper.read(), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#xyzLiteral":
            bio = BytesIO()
            geom.export(bio, file_type="xyz")
            wrapper = TextIOWrapper(bio, encoding='utf-8')
            return Literal(wrapper.read(), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#gltfLiteral":
            bio = BytesIO()
            geom.export(bio, file_type="gltf")
            wrapper = TextIOWrapper(bio, encoding='utf-8')
            return Literal(wrapper.read(), datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#dggsLiteral":
            return Literal(Transformers.transformToDGGS(geom,thegeomsrs),datatype=literaltype)
        elif ltype == "http://www.opengis.net/ont/geosparql#geocodeLiteral":
            return Literal(Transformers.transformToGeocode(geom,thegeomsrs),datatype=literaltype)
        else:
            raise ValueError(
                "The literal type " + str(literaltype) + " is not supported for geometry conversion!"
            )

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

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/area">geof:area</a>: Calculates the area of a 2D geometry provided as a geometry literal .
#  @param a The geometry literal.
#  @returns The area as an <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def area(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.area(thegeom), datatype=XSD.double)


def azimuth(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    minrect = thegeom.minimum_rotated_rectangle
    minrectb = minrect.boundary
    coords = [c for c in minrectb.coords]  # List the line coordinates
    segments = [shapely.geometry.LineString([a, b]) for a, b in zip(coords, coords[1:])]  # Create the four side lines.
    longest_segment = max(segments, key=lambda x: x.length)
    p1, p2 = [c for c in longest_segment.coords]  # List the start and end coordinates of it
    azimuthangle = degrees(atan2(p2[1] - p1[1], p2[0] - p1[0]))
    return Literal(azimuthangle, datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asDGGS">geof:asDGGS</a>: Converts a geometry literal to a DGGS literal .
#  @param a The geometry literal
#  @param dggsType The DGGS type described by a URI
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#dggsLiteral">geo:dggsLiteral</a>
def asDGGS(a: Literal, dggsType) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    #print(a: Literal)
    #print(dggsType)
    #print(Transformers.transformToDGGS(thegeom, dggsType))
    return Literal(Transformers.transformToDGGS(thegeom, dggsType),datatype="http://www.opengis.net/ont/geosparql#dggsLiteral")

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asGeoJSON">geof:asGeoJSON</a>: Converts a geometry literal to a GeoJSON literal .
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#geoJSONLiteral">geo:geoJSONLiteral</a>
def asGeoJSON(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#geoJSONLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#geoJSONLiteral", thegeomsrs)

## Converts a geometry literal to a GLTF literal .
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#gltfLiteral">geo:gltfLiteral</a>
def asGLTF(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#gltfLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#gltfLiteral", thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asGeocode">geof:asGeocode</a>: Converts a geometry literal to a Geocode literal .
#  @param a The geometry literal
#  @param geocodeURI The Geocode type described by a URI
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#geocodeLiteral">geo:geocodeLiteral</a>
def asGeocode(a: Literal, geocodeURI) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print(thegeom)
    print(geocodeURI)
    return Literal(Transformers.transformToGeocode(thegeom, str(geocodeURI)),
                   datatype="http://www.opengis.net/ont/geosparql#geocodeLiteral")


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asGML">geof:asGML</a>: Converts a geometry literal to a GML literal preserving its coordinate reference system. 
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#gmlLiteral">geo:gmlLiteral</a>
def asGML(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#gmlLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#gmlLiteral", thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asKML">geof:asKML</a>: Converts a geometry literal to a KML literal.
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#kmlLiteral">geo:kmlLiteral</a>
def asKML(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#kmlLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#kmlLiteral", thegeomsrs)


## Converts a geometry literal to a OBJ literal .
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#objLiteral">geo:objLiteral</a>
def asOBJ(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#objLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#objLiteral", thegeomsrs)


## Converts a geometry literal to a PLY literal .
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#objLiteral">geo:plyLiteral</a>
def asPLY(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#plyLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#plyLiteral", thegeomsrs)

## Converts a geometry literal to a XYZ literal .
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#xyzLiteral">geo:xyzLiteral</a>
def asXYZ(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#xyzLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a, create3D=True)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#xyzLiteral", thegeomsrs)

## Converts a geometry literal to a WKB literal.
#  Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asWKB">geof:asWKB</a>
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#wkbLiteral">geo:wkbLiteral</a>
def asWKB(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#wkbLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#wkbLiteral", thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/asWKT">geof:asWKT</a>: Converts a geometry literal to a WKT literal.
#  @param a The geometry literal
#  @returns The geometry as a <a target="_blank" href="http://www.opengis.net/ont/geosparql#wktLiteral">geo:wktLiteral</a>
def asWKT(a: Literal) -> Literal:
    if a.datatype=="http://www.opengis.net/ont/geosparql#wktLiteral":
        return a
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom, "http://www.opengis.net/ont/geosparql#wktLiteral", thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/boundary">geof:boundary</a>: Calculates the boundary of a geometry literal.
#  @param a The geometry literal
#  @returns The geometry as a geometry literal in the CRS of the input geometry
def boundary(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.boundary(thegeom), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/boundingCircle">geof:boundingCircle</a>: Calculates the minimum bounding circle of a geometry literal.
#  @param a The geometry literal
#  @returns The bounding circle as a geometry literal in the CRS of the input geometry
def boundingCircle(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.minimum_bounding_circle(thegeom), a.datatype, thegeomsrs)


def buffer(a: Literal, radius, unit) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if isinstance(radius, Literal) and radius.datatype == XSD.double:
        return LiteralUtils.processGeomToLiteral(shapely.buffer(thegeom, float(radius)), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/centroid">geof:centroid</a>: Calculates the centroid of a geometry literal.
#  @param a The geometry literal
#  @returns The centroid as a geometry literal in the CRS of the input geometry
def centroid(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom.centroid, a.datatype, thegeomsrs)


def contains(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.contains(geoms[0], geoms[1]), datatype=XSD.boolean)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/concaveHull">geof:concaveHull</a>: Calculates the concave hull of a geometry literal.
#  @param a The geometry literal
#  @returns The concave hull as a geometry literal in the CRS of the input geometry
def concaveHull(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.concave_hull(thegeom), a.datatype, thegeomsrs)


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
    return Literal(str(1 / (p / (2 * pi * sqrt(a / pi)))), datatype=XSD.double)


def covers(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.covers(geoms[0], geoms[1]), datatype=XSD.boolean)


def coveredBy(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.covered_by(geoms[0], geoms[1]), datatype=XSD.boolean)


def crosses(a: Literal, b: Literal) -> Literal | None | Any:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.crosses(geoms[0], geoms[1]), datatype=XSD.boolean)


def disjoint(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    print(geoms[0])
    print(geoms[1])
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.disjoint(geoms[0], geoms[1]), datatype=XSD.boolean)


def difference(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    print(geomtps)
    print(shapely.difference(geomtps[0][0], geomtps[1][0]))
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.difference(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])


def distance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.distance(geoms[0], geoms[1]), datatype=XSD.double)


def endPoint(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.Point(shapely.get_coordinates(thegeom)[-1]), a.datatype,
                                             thegeomsrs)


def equals(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.equals(geoms[0], geoms[1]), datatype=XSD.boolean)


def envelope(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(thegeom.envelope, a.datatype, thegeomsrs)


def extrude(a: Literal, extrudeval) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.force_3d(shapely.force_2d(thegeom), extrudeval), a.datatype,
                                             thegeomsrs)


def exteriorRing(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.get_exterior_ring(thegeom), a.datatype, thegeomsrs)


def flipXY(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.ops.transform(lambda x, y: (y, x),thegeom), a.datatype, thegeomsrs)


def force2D(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.force_2d(thegeom), a.datatype, thegeomsrs)


def frechetDistance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.frechet_distance(geoms[0], geoms[1]), datatype=XSD.double)


def geometryN(a: Literal, n) -> Literal:
    if isinstance(a, Literal) and isinstance(n, Literal) and n.datatype == XSD.integer:
        thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
        print(thegeom)
        print(shapely.get_geometry(thegeom, int(str(n))))
        return LiteralUtils.processGeomToLiteral(shapely.get_geometry(thegeom, int(str(n))), a.datatype, thegeomsrs)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/geometryType">geof:geometryType</a>: Retrieves the geometry type of a geometry literal.
#  @param a The geometry literal
#  @returns The geometry type as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#string">xsd:string</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def geometryType(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.geom_type, datatype=XSD.string)


def getSRID(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeomsrs, datatype=XSD.anyURI)


def hausDorffDistance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.hausdorff_distance(geoms[0], geoms[1]), datatype=XSD.double)


def inside(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        print(shapely.contains_properly(geoms[1], geoms[0]))
        return Literal(shapely.contains_properly(geoms[1], geoms[0]), datatype=XSD.boolean)


def intersection(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.intersection(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])


def intersection3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, create3D=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(trimesh.boolean.intersection(geoms), datatype=XSD.boolean)


def intersects(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.intersects(geoms[0], geoms[1]), datatype=XSD.boolean)


def intersects3D(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, create3D=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        print(trimesh.boolean.boolean_manifold(geoms, "intersection"))
        return Literal(trimesh.boolean.boolean_manifold(geoms, "intersection"), datatype=XSD.boolean)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/is3D">geof:is3D</a>: Calculates whether a geometry literal represents a 3D geometry.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is threedimensional
def is3D(a: Literal) -> Literal:
    thegeom, thegeomsrs = a.value
    return Literal(thegeom.has_z, datatype=XSD.boolean)


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
    print(thegeom)
    print(shapely.is_empty(thegeom))
    return Literal(shapely.is_empty(thegeom), datatype=XSD.boolean)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/isMeasured">geof:isMeasured</a>: Calculates whether a geometry literal has measurement coordinates.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry has measurement coordinates
def isMeasured(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.has_m, datatype=XSD.boolean)


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
    print(thegeom.is_simple)
    print("The Lit: " + str(Literal(thegeom.is_simple, datatype=XSD.boolean)))
    return Literal(thegeom.is_simple, datatype=XSD.boolean)

## Calculates whether a geometry literal represents a valid geometry.
#  @param a The geometry literal
#  @returns A <a target="_blank" href="http://www.w3.org/2001/XMLSchema#boolean">xsd:boolean</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a> indicating whether the geometry is valid
def isValid(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.is_valid, datatype=XSD.boolean)


def length(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.length, datatype=XSD.double)

## Retrieves the M coordinate of a Point geometry.
#  @param a The geometry literal.
#  @returns The M coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def m(a: Literal) -> Literal:
    thegeom, thegeomsrs = a.value #LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom.geom_type == "Point":
        return Literal(shapely.get_m(thegeom), datatype=XSD.double)


def matrixTransform(a: Literal, matrix) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    shapely.affinity.affine_transform(thegeom, [])
    if thegeom.geom_type == "Point":
        return Literal(shapely.get_m(thegeom), datatype=XSD.double)


## Retrieves the maximum measurement coordinate of a geometry.
#  @param a The geometry literal.
#  @returns The maximum measurement coordinate as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def maxM(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    clist = shapely.get_coordinates(thegeom, include_m=True).tolist()
    flinf = -float("inf")
    maxM = flinf
    for c in clist:
        if c[2] != nan and maxM < c[2]:
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
    clist = shapely.get_coordinates(thegeom, include_z=True).tolist()
    flinf = -float("inf")
    maxZ = flinf
    for c in clist:
        if c[2] != nan and maxZ < c[2]:
            maxZ = c[2]
    if maxZ == flinf:
        maxZ = "NaN"
    return Literal(str(maxZ), datatype=XSD.double)

## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/metricArea">geof:metricArea</a>: Calculates the area of a 2D geometry provided as a geometry literal in squaremeters.
#  @param a The geometry literal.
#  @returns The area in squaremeters as an <a target="_blank" href="http://www.w3.org/2001/XMLSchema#double">xsd:double</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def metricArea(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    return Literal(shapely.area(normgeom), datatype=XSD.double)


def metricBuffer(a: Literal, radius) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    if isinstance(radius, Literal) and radius.datatype == XSD.double:
        return LiteralUtils.processGeomToLiteral(shapely.buffer(normgeom, float(radius)), a.datatype, thegeomsrs)


def metricDistance(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, normsrs=3857)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.distance(geoms[0], geoms[1]), datatype=XSD.double)


def metricLength(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    return Literal(shapely.length(normgeom), datatype=XSD.double)


def metricPerimeter(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    normgeom = Transformers.transformToSRS(thegeom, thegeomsrs, 3857)
    return Literal(normgeom.length, datatype=XSD.double)


def metricWithinDistance(a: Literal, b, d) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True, normsrs=3857)))[0]
    if isinstance(d, Literal) and d.datatype == XSD.double:
        distance = float(str(d))
        return Literal(shapely.dwithin(geoms[0], geoms[1], distance), datatype=XSD.boolean)


def minimumBoundingRadius(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.minimum_bounding_radius(thegeom), datatype=XSD.double)


def minimumClearance(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.minimum_clearance(thegeom), datatype=XSD.double)


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
        if c[2] != nan and minM > c[2]:
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
    clist = shapely.get_coordinates(thegeom, include_z=True).tolist()
    flinf = float("inf")
    minZ = flinf
    for c in clist:
        print(c)
        if c[2] != nan and minZ > c[2]:
            minZ = c[2]
    if minZ == flinf:
        minZ = "NaN"
    return Literal(str(minZ), datatype=XSD.double)


def numGeometries(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.get_num_geometries(thegeom), datatype=XSD.integer)


def numInteriorRing(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.get_num_interior_rings(thegeom), datatype=XSD.integer)


def numPatches(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(len(shapely.get_parts(thegeom)), datatype=XSD.integer)


def numPoints(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.count_coordinates(thegeom), datatype=XSD.integer)


def patchN(a: Literal, n) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.get_parts(thegeom).tolist()[n], a.datatype)


def pointN(a: Literal, n) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if "Polygon" in str(thegeom.geom_type):
        return LiteralUtils.processGeomToLiteral(shapely.get_point(shapely.get_exterior_ring(thegeom), int(str(n))), a.datatype, thegeomsrs)
    return LiteralUtils.processGeomToLiteral(shapely.get_point(thegeom, int(str(n))), a.datatype, thegeomsrs)


def pointOnSurface(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print(shapely.point_on_surface(thegeom))
    return LiteralUtils.processGeomToLiteral(shapely.point_on_surface(thegeom), a.datatype, thegeomsrs)


def perimeter(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(thegeom.length, datatype=XSD.double)


def overlaps(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.overlaps(geoms[0], geoms[1]), datatype=XSD.boolean)


def relate(a: Literal, b, matrix) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.relate_pattern(geoms[0], geoms[1], str(matrix)), datatype=XSD.boolean)


def reverse(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.reverse(thegeom), a.datatype, thegeomsrs)


def scale(a: Literal, scaleX, scaleY, scaleZ) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print(shapely.affinity.scale(thegeom, xfact=float(scaleX.value), yfact=float(scaleY.value),
                                 zfact=float(scaleZ.value)))
    return LiteralUtils.processGeomToLiteral(
        shapely.affinity.scale(thegeom, xfact=float(scaleX.value), yfact=float(scaleY.value),
                               zfact=float(scaleZ.value)), a.datatype, thegeomsrs)


def shortestLine(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    print(geomtps)
    print(geomtps[0][0])
    print(geomtps[1][0])
    print(shapely.shortest_line(geomtps[0][0], geomtps[1][0]))
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.shortest_line(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])


def simplify(a: Literal, tolerance) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.simplify(thegeom, float(tolerance)), a.datatype, thegeomsrs)


def skew(a: Literal, xs, ys) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.affinity.skew(thegeom, xs, ys), a.datatype, thegeomsrs)


## Implements <a target="_blank" href="http://www.opengis.net/def/function/geosparql/spatialDimension">geof:spatialDimension</a>: Calculates the spatial dimension of a geometry literal.
#  @param a The geometry literal
#  @returns The spatial dimension as a <a target="_blank" href="http://www.w3.org/2001/XMLSchema#integer">xsd:integer</a> <a target="_blank" href="http://www.w3.org/TR/rdf-concepts/#section-Graph-Literal">Literal</a>
def spatialDimension(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return Literal(shapely.get_dimensions(thegeom), datatype=XSD.integer)


def startPoint(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    return LiteralUtils.processGeomToLiteral(shapely.Point(shapely.get_coordinates(thegeom)[0]), a.datatype, thegeomsrs)


def symDifference(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.symmetric_difference(geomtps[0][0], geomtps[1][0]), a.datatype,
                                                 geomtps[0][1])


def transform(a: Literal, srsIRI) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    print("TRANSFORM FUNCTION")
    geom=Transformers.transformToSRS(thegeom, thegeomsrs, srsIRI)
    print("GEOM: "+str(geom))
    print("AS LITERAL: "+str(LiteralUtils.processGeomToLiteral(geom, a.datatype,srsIRI)))
    if thegeom is not None and thegeomsrs is not None:
        return LiteralUtils.processGeomToLiteral(Transformers.transformToSRS(thegeom, thegeomsrs, srsIRI), a.datatype,srsIRI)
    raise ValueError("An invalid geometry literal was provided or an illegal transformation requested for function geof:transform")


def transformCRS84(a: Literal) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if thegeom is not None and thegeomsrs is not None:
        return LiteralUtils.processGeomToLiteral(Transformers.transformToSRS(thegeom, thegeomsrs, CRS84URI), a.datatype,
                                                 CRS84URI)
    raise ValueError(
        "An invalid geometry literal was provided or an illegal transformation requested for function geof:transformCRS84")


def translate(a: Literal, deltaX, deltaY, deltaZ) -> Literal:
    thegeom, thegeomsrs = LiteralUtils.processLiteralTypeToGeom(a)
    if (isinstance(deltaX, Literal) and deltaX.datatype == XSD.double and isinstance(deltaY,
                                                                                     Literal) and deltaY.datatype == XSD.double and isinstance(
            deltaZ, Literal) and deltaZ.datatype == XSD.double):
        return LiteralUtils.processGeomToLiteral(
            shapely.affinity.translate(thegeom, float(deltaX.value), float(deltaY.value), float(deltaZ.value)),
            a.datatype, thegeomsrs)
    raise ValueError("Invalid parameters were provided for function geof:translate")


def touches(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.touches(geoms[0], geoms[1]), datatype=XSD.boolean)
    raise ValueError("Invalid parameters were provided for function geof:touches")


def union(a: Literal, b: Literal) -> Literal:
    geomtps = LiteralUtils.processLiteralsToGeom([a, b], normalize=True)
    if len(geomtps) > 1:
        return LiteralUtils.processGeomToLiteral(shapely.union(geomtps[0][0], geomtps[1][0]), a.datatype, geomtps[0][1])
    raise ValueError("Invalid parameters were provided for function geof:union")


def within(a: Literal, b: Literal) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if geoms[0] is not None and geoms[1] is not None:
        return Literal(shapely.within(geoms[0], geoms[1]), datatype=XSD.boolean)
    raise ValueError("Invalid parameters were provided for function geof:within")


def withinDistance(a: Literal, b, d) -> Literal:
    geoms = list(zip(*LiteralUtils.processLiteralsToGeom([a, b], normalize=True)))[0]
    if isinstance(d, Literal) and d.datatype == XSD.double:
        distance = float(str(d))
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
    URIRef(GEOF + "asDGGS"): asDGGS,
    URIRef(GEOF + "asGeoJSON"): asGeoJSON,
    URIRef(GEOF + "asGML"): asGML,
    URIRef(GEOF + "asKML"): asKML,
    URIRef(GEOF + "asWKB"): asWKB,
    URIRef(GEOF + "asWKT"): asWKT,
    URIRef(GEOF + "boundingCircle"): boundingCircle,
    URIRef(GEOF + "centroid"): centroid,
    URIRef(GEOF + "concaveHull"): concaveHull,
    URIRef(GEOF + "coordinateDimension"): coordinateDimension,
    URIRef(GEOF + "endPoint"): endPoint,
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
    URIRef(GEOF + "startPoint"): startPoint,
    URIRef(GEOF + "transform"): transform,
}

geosparql13 = {
    URIRef(GEOFEXT + "asGeocode"): asGeocode,
    URIRef(GEOFEXT + "asGLTF"): asGLTF,
    URIRef(GEOFEXT + "asOBJ"): asOBJ,
    URIRef(GEOFEXT + "asPLY"): asPLY,
    URIRef(GEOFEXT + "asWKB"): asWKB,
    URIRef(GEOFEXT + "asXYZ"): asXYZ,
    URIRef(GEOFEXT + "azimuth"): azimuth,
    URIRef(GEOFEXT + "compactnessRatio"): compactnessRatio,
    URIRef(GEOFEXT + "endPoint"): endPoint,
    URIRef(GEOFEXT + "exteriorRing"): exteriorRing,
    URIRef(GEOFEXT + "force2D"): force2D,
    URIRef(GEOFEXT + "force3D"): extrude,
    URIRef(GEOFEXT + "frechetDistance"): frechetDistance,
    URIRef(GEOFEXT + "flipXY"): flipXY,
    URIRef(GEOFEXT + "hausdorffDistance"): hausDorffDistance,
    URIRef(GEOFEXT + "intersects3D"): intersects3D,
    URIRef(GEOFEXT + "isCollection"): isCollection,
    URIRef(GEOFEXT + "isClosed"): isClosed,
    URIRef(GEOFEXT + "isRing"): isRing,
    URIRef(GEOFEXT + "isValid"): isValid,
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
    URIRef(GEOFEXT + "patchN"): patchN,
    URIRef(GEOFEXT + "pointN"): pointN,
    URIRef(GEOFEXT + "pointOnSurface"): pointOnSurface,
    URIRef(GEOFEXT + "reverse"): reverse,
    URIRef(GEOFEXT + "scale"): scale,
    URIRef(GEOFEXT + "shortestLine"): shortestLine,
    URIRef(GEOFEXT + "simplify"): simplify,
    URIRef(GEOFEXT + "skew"): skew,
    URIRef(GEOFEXT + "startPoint"): startPoint,
    URIRef(GEOFEXT + "transformCRS84"): transformCRS84,
    URIRef(GEOFEXT + "translate"): translate,
    URIRef(GEOFEXT + "withinDistance"): withinDistance,
    URIRef(GEOFEXT + "X"): x,
    URIRef(GEOFEXT + "Y"): y,
    URIRef(GEOFEXT + "Z"): z,
}


def getfuncs():
    thefuncs = merge_dicts(geosparql10, geosparql11, geosparql13)
    for uri in thefuncs:
        try:
            register_custom_function(uri, thefuncs[uri])
            print("Registered custom function", uri)
            # print(thefuncs[uri])
        except ValueError:
            pass
        except AttributeError:
            pass

    term.bind(URIRef(str(GEO)+"wktLiteral"),shapely.Geometry,LiteralUtils.processWKTLiteral,LiteralUtils.processGeomToWKTLiteral)


getfuncs()

g = Graph()
dir_path = os.path.dirname(os.path.realpath(__file__))
#g.parse(dir_path + "/../tests/testdata.ttl")

result = g.query(
    """
PREFIX my: <http://example.org/ApplicationSchema#>
PREFIX geo: <"""+str(GEO)+""">
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX geof: <"""+str(GEOF)+""">
SELECT ?sline ?literal
WHERE {
  BIND("<http://www.opengis.net/def/crs/OGC/1.3/CRS84> Polygon((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))"^^geo:wktLiteral as ?literal)
  BIND(geof:is3D(?literal) AS ?sline)
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
