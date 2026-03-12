import shapely.geometry
from rdflib import Graph, Literal
import os
import trimesh
import itertools
from shapely.testing import assert_geometries_equal
from geosparql.geosparql import LiteralUtils
from geosparql.geosparql_aggregates import processLiteralTypeToGeom
from test_geosparql11 import TestGeoSPARQL11
from testutils import TestUtils

GEO = "http://www.opengis.net/ont/geosparql#"
GEOF = "http://www.opengis.net/def/function/geosparql/ext/"
GEOFEXT = "http://www.opengis.net/def/function/geosparql/ext/"
GEOPREFIX="geo:"
GEOFPREFIX="geof:"
GEOFEXTPREFIX="geofext:"
eqtolerance=1e-3


# image showing cells is in tests folder
g = Graph()
dir_path = os.path.dirname(os.path.realpath(__file__))
g.parse(dir_path+"/testdata.ttl")
config={
    "literalTypes":{
        "WKT":"geo:wktLiteral",
        "GML":"geo:gmlLiteral",
        "GeoJSON":"geo:geoJSONLiteral",
        "KML":"geo:kmlLiteral",
        #"GeoCode":"geo:geocodeLiteral"
        #"DGGS":"geo:dggsLiteral"
    },
    "literalTypesM": {
        "WKT": "geo:wktLiteral",
        #"GML": "geo:gmlLiteral",
    },
    "geoProperties":{
        "WKT":"geo:asWKT",
        "GML":"geo:asGML",
        "GeoJSON":"geo:asGeoJSON",
        "KML":"geo:asKML",
        #"GeoCode": "geo:asGeocode"
        #"DGGS":"geo:asDGGS"
    },
    "geoPropertiesM": {
        "WKT": "geo:asWKT",
        #"GML": "geo:asGML",
    }
}
combinations=list(itertools.permutations(config["geoProperties"],2))
combinations = list(map(lambda x, y: (x, y), config["literalTypes"].keys(), config["literalTypes"].keys())) + combinations
combinationsM=list(itertools.permutations(config["geoPropertiesM"],2))
combinationsM = list(map(lambda x, y: (x, y), config["literalTypesM"].keys(), config["literalTypesM"].keys())) + combinationsM
print(combinations)
print(combinationsM)
ltypes=config["literalTypes"].keys()
ltypesM=config["literalTypesM"].keys()


class TestGeoSPARQLExt(TestGeoSPARQL11):

    def test_asGeocode(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?gc
        WHERE {
          my:A geo:hasGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:asGeocode(?aLiteral,"http://opengis.net/ont/geocode/OpenLocationCode") as ?gc)
        }
        """,combinations,config, g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["gc"])=="<http://opengis.net/ont/geocode/OpenLocationCode> 2G8PJ822+22"

    def test_asGLTF(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?gltf
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:asGLTF(?aLiteral) as ?gltf)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            print("Testing with " + str(res[1]))
            result = res[0]
            assert len(result) == 1
            assert str(result[0][
                           "gltf"]) == "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))"

    def test_asOBJ(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?obj
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:asOBJ(?aLiteral) as ?obj)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            print("Testing with " + str(res[1]))
            result = res[0]
            assert len(result) == 1
            assert str(result[0]["obj"]) == "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))"

    def test_asPLY(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?ply
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:asPLY(?aLiteral) as ?ply)
            }
            """ ,combinations,config,g)
        express="""ply
format ascii 1.0
comment https://github.com/mikedh/trimesh
element vertex 8
property float x
property float y
property float z
element face 12
property list uchar int vertex_indices
end_header
-83.59999847 34.09999847 0.00000000
-83.19999695 34.09999847 0.00000000
-83.19999695 34.50000000 0.00000000
-83.59999847 34.50000000 0.00000000
-83.59999847 34.09999847 3.00000000
-83.19999695 34.09999847 3.00000000
-83.19999695 34.50000000 3.00000000
-83.59999847 34.50000000 3.00000000
3 1 0 3
3 3 2 1
3 7 4 5
3 5 6 7
3 5 4 1
3 1 4 0
3 6 5 2
3 2 5 1
3 4 7 0
3 0 7 3
3 7 6 3
3 3 6 2"""
        expresult = trimesh.load(file_obj=trimesh.util.wrap_as_stream(express),file_type="ply",encoding="ascii")
        for res in resultlist:
            print("Testing with " + str(res[1]))
            result = res[0]
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["ply"])[0], expresult)

    def test_asWKB(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?wkb
        WHERE {
          my:A geo:hasGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:asWKB(?aLiteral) as ?wkb)
        }
        """,combinations,config, g)
        expresult=shapely.from_wkt("POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(processLiteralTypeToGeom(result[0]["wkb"])[0], expresult)

    def test_asXYZ(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?xyz
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:asXYZ(?aLiteral) as ?xyz)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            print("Testing with " + str(res[1]))
            result = res[0]
            assert len(result) == 1
            assert str(result[0][
                           "xyz"]) == "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))"

    def test_azimuth(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?azimuth
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:azimuth(?aLiteral) as ?azimuth)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["azimuth"]) == "90.0"

    def test_closestPoint(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?cPoint
        WHERE {
          my:A my:hasPointGeometry ?aGeom .
          ?aGeom geo:asWKT ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom geo:asWKT ?dLiteral .
          BIND (geof:closestPoint(?aLiteral, ?dLiteral) as ?cPoint)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POINT (-83.4 34.3)")
        for res in resultlist:
            result=res[0]
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["cPoint"])[0],expresult,tolerance=eqtolerance)

    def test_compactnessRatio(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?cratio
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:compactnessRatio(?aLiteral) as ?cratio)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["cratio"]) == "0.886226925452758"

    def test_endPoint(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX geof: <"""+str(GEOF)+""">
        SELECT ?endPoint
        WHERE {
          my:AExactGeom %%literalrel1%% ?literal .
          BIND(geof:endPoint(?literal) AS ?endPoint)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POINT (-83.6 34.1)")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["endPoint"])[0], expresult)

    def test_exteriorRing(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX geof: <"""+str(GEOF)+""">
        SELECT ?exRing
        WHERE {
          my:AExactGeom %%literalrel1%% ?literal .
          BIND(geof:exteriorRing(?literal) AS ?exRing)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("LINESTRING (-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1)")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            #Results vary by literal between LineString and LinearRing. Normalized for LineString here
            litres=Literal(str(result[0]["exRing"]).replace("LINEARRING","LINESTRING").replace("LinearRing","LineString"),datatype=result[0]["exRing"].datatype)
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(litres)[0], expresult)

    def test_flipXY(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX geof: <"""+str(GEOF)+""">
        SELECT ?flipXY
        WHERE {
          my:NExactGeom %%literalrel1%% ?literal .
          BIND(geof:flipXY(?literal) AS ?flipXY)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((38.913574 -77.089005, 38.913574 -77.029953,  38.886321 -77.029953,  38.886321 -77.089005,  38.913574 -77.089005))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            print(result)
            print(res)
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["flipXY"])[0],expresult,tolerance=eqtolerance)

    def test_farthestCoordinate(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?farthestCoord
        WHERE {
          my:A my:hasPointGeometry ?aGeom .
          ?aGeom geo:asWKT ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom geo:asWKT ?dLiteral .
          BIND (geof:farthestCoordinate(?aLiteral, ?dLiteral) as ?farthestCoord)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POINT (-83.4 34.3)")
        for res in resultlist:
            result=res[0]
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["farthestCoord"])[0],expresult,tolerance=eqtolerance)

    def test_frechetdistance(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?fdistance
        WHERE {
          my:C geo:hasDefaultGeometry ?cGeom .
          ?cGeom %%literalrel1%% ?cLiteral .
          my:F geo:hasDefaultGeometry ?fGeom .
          ?fGeom %%literalrel2%% ?fLiteral .
          BIND (geof:frechetDistance(?cLiteral, ?fLiteral) as ?fdistance)
        }
        """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["fdistance"]) == "0.41231056256177195"

    def test_force2D(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX geof: <"""+str(GEOF)+""">
        SELECT ?force2D
        WHERE {
          my:NExactGeom %%literalrel1%% ?literal .
          BIND(geof:force2D(?literal) AS ?force2D)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((-77.089005 38.913574, -77.029953 38.913574, -77.029953 38.886321, -77.089005 38.886321, -77.089005 38.913574))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["force2D"])[0],expresult,tolerance=eqtolerance)


    def test_haussdorffdistance(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?hdistance
        WHERE {
          my:C geo:hasDefaultGeometry ?cGeom .
          ?cGeom %%literalrel1%% ?cLiteral .
          my:F geo:hasDefaultGeometry ?fGeom .
          ?fGeom %%literalrel2%% ?fLiteral .
          BIND (geof:hausdorffDistance(?cLiteral, ?fLiteral) as ?hdistance)
        }
        """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["hdistance"]) == "0.41231056256177195"

    def test_intersects3D(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfIntersects) as ?intersects)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom %%literalrel2%% ?dLiteral .
          BIND (geof:Intersects3D(?aLiteral, ?dLiteral) as ?sfIntersects)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["intersects"]) == "true"

    def test_isClosed(self):
        resultlist = TestUtils.queryExecution(
        """PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?isAClosed ?isEClosed {
                <http://example.org/ApplicationSchema#AExactGeom> %%literalrel1%% ?a_wkt .
                BIND(geof:isClosed(?a_wkt) AS ?isAClosed)
                <http://example.org/ApplicationSchema#EExactGeom> %%literalrel1%% ?e_wkt .
                BIND(geof:isClosed(?e_wkt) AS ?isEClosed)
            }
        """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["isAClosed"]) == "true"
            assert str(result[0]["isEClosed"]) == "false"

    def test_isCollection(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
                PREFIX geof: <"""+str(GEOF)+""">
                SELECT ?isC1 ?isC2 ?isC3 {
                    BIND(geof:isCollection("GEOMETRYCOLLECTION (MULTIPOINT((0 0), (1 1)), POINT(3 4), LINESTRING(2 3, 3 4))"^^geo:wktLiteral) AS ?isC1)
                    BIND(geof:isCollection("MULTIPOLYGON (((1 1, 1 3, 3 3, 3 1, 1 1)), ((4 3, 6 3, 6 1, 4 1, 4 3)))"^^geo:wktLiteral) AS ?isC2)
                    BIND(geof:isCollection("POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0), (1 1, 1 2, 2 2, 2 1, 1 1))"^^geo:wktLiteral) AS ?isC3)
                }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["isC1"]) == "true"
            assert str(result[0]["isC2"]) == "true"
            assert str(result[0]["isC3"]) == "false"

    def test_isRing(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
                PREFIX geof: <"""+str(GEOF)+""">
                SELECT ?isARing ?isORing {
                    <http://example.org/ApplicationSchema#AExactGeom> %%literalrel1%% ?a_wkt .
                    BIND(geof:isRing(?a_wkt) AS ?isARing)
                            <http://example.org/ApplicationSchema#OExactGeom> %%literalrel1%% ?o_wkt .
                    BIND(geof:isRing("POINT M (1 2 3)"^^geo:wktLiteral) AS ?isORing)
                }
            """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["isARing"]) == "true"
            assert str(result[0]["isORing"]) == "false"

    def test_isTriangle(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
                PREFIX geof: <"""+str(GEOF)+""">
                SELECT ?isTriangle ?isNoTriangle {
                    <http://example.org/ApplicationSchema#AExactGeom> %%literalrel1%% ?a_wkt .
                    BIND(geof:isTriangle(?a_wkt) AS ?isNoTriangle)
                    BIND(geof:isTriangle("POLYGON ((0 0,0 1,1 1,0 0))"^^geo:wktLiteral) AS ?isTriangle)
                }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["isTriangle"]) == "true"
            assert str(result[0]["isNoTriangle"]) == "false"

    def test_isRectangle(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
                PREFIX geof: <"""+str(GEOF)+""">
                SELECT ?isRectangle ?isNoRectangle {
                    <http://example.org/ApplicationSchema#AExactGeom> %%literalrel1%% ?a_wkt .
                    BIND(geof:isRectangle(?a_wkt) AS ?isNoRectangle)
                    BIND(geof:isRectangle(geof:envelope(?a_wkt)) AS ?isRectangle)
                }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["isRectangle"]) == "true"
            assert str(result[0]["isNoRectangle"]) == "false"

    def test_isValid(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
                PREFIX geof: <"""+str(GEOF)+""">
                SELECT ?isValid ?isNotValid {
                    <http://example.org/ApplicationSchema#AExactGeom> %%literalrel1%% ?a_wkt .
                    BIND(geof:isValid(?a_wkt) AS ?isValid)
                            <http://example.org/ApplicationSchema#OExactGeom> %%literalrel1%% ?o_wkt .
                    BIND(geof:isValid("POLYGON((0 0, 10 10, 0 10, 10 0, 0 0))"^^geo:wktLiteral) AS ?isNotValid)
                }
            """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["isValid"]) == "true"
            assert str(result[0]["isNotValid"]) == "false"

    def test_isValidTrajectory(self):
        resultlist = TestUtils.queryExecution(
        """PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?isValidT ?isNotValidT2 ?isNotValidT {
                <http://example.org/ApplicationSchema#AExactGeom> %%literalrel1%% ?a_wkt .
                BIND(geof:isValidTrajectory(?a_wkt) AS ?isNotValidT)
                <http://example.org/ApplicationSchema#OExactGeom> %%literalrel1%% ?o_wkt .
                BIND(geof:isValidTrajectory(?o_wkt) AS ?isNotValidT2)
                BIND(geof:isValidTrajectory("LineString M(0 0 1, 10 10 2, 0 10 3, 10 0 4, 0 0 5)"^^geo:wktLiteral) AS ?isValidT)
            }
        """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["isValidT"]) == "true"
            assert str(result[0]["isNotValidT"]) == "false"
            assert str(result[0]["isNotValidT2"]) == "false"

    def test_longestLine(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?longestLine
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom geo:asWKT ?aLiteral .
              my:D geo:hasDefaultGeometry ?dGeom .
              ?dGeom geo:asWKT ?dLiteral .
              BIND (geof:longestLine(?aLiteral, ?dLiteral) as ?longestLine)
            }
            """ ,combinationsM,config,g)
        expresult=shapely.from_wkt("LINESTRING (-83.6 34.5, -83.1 34)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["longestLine"])[0], expresult)

    def test_M(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?m
            WHERE {
              my:PPointGeom %%literalrel1%% ?literal .
              BIND(geof:M(?literal) AS ?m)
            }
            """ ,combinationsM,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["m"]) == "5.0"

    def test_maxDistance(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?maxDistance
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom geo:asWKT ?aLiteral .
              my:D geo:hasDefaultGeometry ?dGeom .
              ?dGeom geo:asWKT ?dLiteral .
              BIND (geof:maxDistance(?aLiteral, ?dLiteral) as ?maxDistance)
            }
            """ ,combinationsM,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["maxDistance"]) == "0.7071067811865476"

    def test_maxM(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?maxM
            WHERE {
              my:PExactGeom %%literalrel1%% ?literal .
              BIND(geof:maxM(?literal) AS ?maxM)
            }
            """ ,combinationsM,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["maxM"]) == "10.0"

    def test_metricWithinDistance(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?wdistance) as ?wddistance)
            WHERE {
              my:C geo:hasDefaultGeometry ?cGeom .
              ?cGeom %%literalrel1%% ?cLiteral .
              my:F geo:hasDefaultGeometry ?fGeom .
              ?fGeom %%literalrel2%% ?fLiteral .
              BIND (geof:metricWithinDistance(?cLiteral, ?fLiteral,"5.0"^^xsd:double) as ?wdistance)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            print(result[0])
            assert str(result[0]["wddistance"]) == "false"

    def test_minimumBoundingRadius(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?bradius
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:minimumBoundingRadius(?aLiteral) as ?bradius)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["bradius"]) == "0.28284271247460796"

    def test_minimumClearance(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?mclearance
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:minimumClearance(?aLiteral) as ?mclearance)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["mclearance"]) == "0.3999999999999915"

    def test_minimumClearanceLine(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?mclearancel
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:minimumClearanceLine(?aLiteral) as ?mclearancel)
            }
            """ ,combinations,config,g)
        expresult = shapely.from_wkt("LINESTRING (-83.6 34.1, -83.2 34.1)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["mclearancel"])[0], expresult)
    
    def test_minM(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?minM
            WHERE {
              my:PExactGeom %%literalrel1%% ?literal .
              BIND(geof:minM(?literal) AS ?minM)
            }
            """ ,combinationsM,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["minM"]) == "5.0"


    def test_numInteriorRing(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?numInteriorRing
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:numInteriorRing(?literal) AS ?numInteriorRing)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["numInteriorRing"]) == "0"

    def test_numPatches(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?numPatches
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:numPatches(?literal) AS ?numPatches)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["numPatches"]) == "1"

    def test_numPoints(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?numPoints
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:numPoints(?literal) AS ?numPoints)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["numPoints"]) == "5"

    def test_pointN(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?pointN
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:pointN(?literal,"1"^^xsd:integer) AS ?pointN)
            }
            """,combinations,config, g)
        expresult=shapely.from_wkt("POINT (-83.2 34.1)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["pointN"])[0],expresult,tolerance=eqtolerance)
            #assert str(result[0]["pointN"]) == "POINT (-83.3 34.3)"

    def test_pointOnSurface(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?pointOnSurface
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:pointOnSurface(?literal) AS ?pointOnSurface)
            }
            """,combinations,config,g)
        expresult=shapely.from_wkt("POINT (-83.3 34.3)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(processLiteralTypeToGeom(result[0]["pointOnSurface"])[0],expresult,tolerance=eqtolerance)

    def test_reverse(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?reverse
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:reverse(?literal) AS ?reverse)
            }
            """ ,combinations,config,g)
        expresult = shapely.from_wkt("POLYGON ((-83.6 34.1, -83.6 34.5, -83.2 34.5, -83.2 34.1, -83.6 34.1))")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["reverse"])[0], expresult)

    def test_scale(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?scale
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:scale(?literal,"2.0"^^xsd:double,"2.0"^^xsd:double,"2.0"^^xsd:double) AS ?scale)
            }
            """ ,combinations,config,g)
        expresult = shapely.from_wkt("POLYGON ((-83.8 33.9, -83 33.9, -83 34.7, -83.8 34.7, -83.8 33.9))")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["scale"])[0], expresult)

    def test_shortestLine(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?sline
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              my:OExactGeom %%literalrel2%% ?literal2 .
              BIND(geof:shortestLine(?literal,?literal2) AS ?sline)
            }
            """ ,combinations,config,g)
        expresult = shapely.from_wkt("LINESTRING (-83.2 34.5, 2.393 47.448)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["sline"])[0], expresult)

    def test_simplify(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?simple
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:simplify(?literal,"1.5"^^xsd:double) AS ?simple)
            }
            """ ,combinations,config,g)
        expresult = shapely.from_wkt("POLYGON ((-83.6 34.5, -83.2 34.1, -83.2 34.5, -83.6 34.5))")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["simple"])[0], expresult)


    def test_translate(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?translate
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:translate(?literal,"1.0"^^xsd:double,"1.0"^^xsd:double,"1.0"^^xsd:double) AS ?translate)
            }
            """ ,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((-82.6 35.1, -82.2 35.1, -82.2 35.5, -82.6 35.5, -82.6 35.1))")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["translate"])[0], expresult)

    def test_transformCRS84(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?transformed
            WHERE {
              my:LExactGeom %%literalrel1%% ?literal .
              BIND(geof:transformCRS84(?literal) AS ?transformed)
            }
            """ ,combinations,config,g)
        expresult=shapely.from_wkt("Point(-88.38 31.95)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["transformed"])[0], expresult)

    def test_startPoint(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?startPoint
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:startPoint(?literal) AS ?startPoint)
            }
            """ ,combinations,config,g)
        expresult = shapely.from_wkt("POINT (-83.6 34.1)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["startPoint"])[0], expresult)

    def test_withinDistance(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?wdistance
            WHERE {
              my:C geo:hasDefaultGeometry ?cGeom .
              ?cGeom %%literalrel1%% ?cLiteral .
              my:F geo:hasDefaultGeometry ?fGeom .
              ?fGeom %%literalrel2%% ?fLiteral .
              BIND (geof:withinDistance(?cLiteral, ?fLiteral,"5.0"^^xsd:double) as ?wdistance)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["wdistance"]) == "true"

    def test_X(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?x
            WHERE {
              my:FExactGeom %%literalrel1%% ?literal .
              BIND(geof:X(?literal) AS ?x)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["x"]) == "-83.4"

    def test_Y(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?y
            WHERE {
              my:FExactGeom %%literalrel1%% ?literal .
              BIND(geof:Y(?literal) AS ?y)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["y"]) == "34.4"

    def test_Z(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?z
            WHERE {
              my:NPointGeom %%literalrel1%% ?literal .
              BIND(geof:Z(?literal) AS ?z)
            }
            """ ,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["z"]) == "1.0"