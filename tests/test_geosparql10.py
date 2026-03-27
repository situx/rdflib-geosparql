import shapely.geometry
from rdflib import Graph, Namespace
import os
import itertools
from shapely.testing import assert_geometries_equal
from geosparql.geosparql import LiteralUtils
from testutils import TestUtils

GEO = Namespace("http://www.opengis.net/ont/geosparql#")
GEOF = Namespace("http://www.opengis.net/def/function/geosparql/")
GEOFEXT = Namespace("http://www.opengis.net/def/function/geosparql/ext/")
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
        "GML":"geo:gmlLiteral"
    },
    "geoProperties":{
        "WKT":"geo:asWKT",
        "GML":"geo:asGML"
    }
}
combinations=list(itertools.permutations(config["geoProperties"],2))
combinations = list(map(lambda x, y: (x, y), config["literalTypes"].keys(), config["literalTypes"].keys())) + combinations
print(combinations)
scombinations=[("WKT","WKT")]
print(scombinations)

class TestGeoSPARQL10:

    def test_buffer(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?buffer
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:buffer(?aLiteral,"5.0"^^xsd:double,<http://www.ontology-of-units-of-measure.org/resource/om-2/meter>) as ?buffer)
            }
            """,combinations,config, g)
        expresult = shapely.from_wkt(
            """POLYGON ((-88.6 34.1, -88.6 34.5, -88.50392640201615 35.47545161008064, -88.21939766255643 36.41341716182545, -87.75734806151272 37.277851165098014, -87.13553390593273 38.03553390593274, -86.37785116509801 38.65734806151273, -85.51341716182544 39.11939766255644, -84.57545161008063 39.403926402016154, -83.6 39.5, -83.2 39.5, -82.22454838991936 39.403926402016154, -81.28658283817455 39.11939766255644, -80.42214883490199 38.65734806151273, -79.66446609406727 38.03553390593274, -79.04265193848728 37.277851165098014, -78.58060233744357 36.41341716182545, -78.29607359798385 35.47545161008064, -78.2 34.5, -78.2 34.1, -78.29607359798385 33.12454838991936, -78.58060233744357 32.18658283817455, -79.04265193848728 31.32214883490199, -79.66446609406727 30.564466094067264, -80.42214883490199 29.942651938487273, -81.28658283817455 29.480602337443568, -82.22454838991936 29.196073597983847, -83.2 29.1, -83.6 29.1, -84.57545161008063 29.196073597983847, -85.51341716182544 29.480602337443568, -86.37785116509801 29.942651938487273, -87.13553390593273 30.564466094067264, -87.75734806151272 31.32214883490199, -88.21939766255643 32.18658283817455, -88.50392640201615 33.12454838991936, -88.6 34.1))""")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["buffer"])[0], expresult)

    def test_convexHull(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?chull
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:convexHull(?aLiteral) as ?chull)
            }
            """,combinations,config, g)
        expresult = shapely.from_wkt("POLYGON ((-83.6 34.1, -83.6 34.5, -83.2 34.5, -83.2 34.1, -83.6 34.1))")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["chull"])[0], expresult)

    def test_boundary(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?boundary
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:boundary(?aLiteral) as ?boundary)
            }
            """, combinations, config, g)
        expresult = shapely.from_wkt("LINESTRING (-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["boundary"])[0], expresult)

    def test_distance(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?distance
        WHERE {
          my:C geo:hasDefaultGeometry ?cGeom .
          ?cGeom %%literalrel1%% ?cLiteral .
          my:F geo:hasDefaultGeometry ?fGeom .
          ?fGeom %%literalrel2%% ?fLiteral .
          BIND (geof:distance(?cLiteral, ?fLiteral,"http://www.opengis.net/def/uom/OGC/1.0/meter"^^xsd:anyURI) as ?distance)
        }
        """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["distance"]) == "0.20000000000000284"
    
    def test_difference(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?difference
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom %%literalrel2%% ?dLiteral .
          BIND (geof:difference(?aLiteral, ?dLiteral) as ?difference)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((-83.6 34.1, -83.6 34.5, -83.2 34.5, -83.2 34.2, -83.3 34.2, -83.3 34.1, -83.6 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["difference"])[0],expresult,tolerance=eqtolerance)
    
    def test_envelope(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?envelope
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:envelope(?aLiteral) as ?envelope)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["envelope"])[0], expresult)
    
    def test_ehEquals(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?ehEquals) as ?equals) (xsd:boolean(?ehEquals2) as ?equals2)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:B geo:hasDefaultGeometry ?bGeom .
          ?bGeom %%literalrel2%% ?bLiteral .
          BIND (geof:ehEquals(?aLiteral, ?aLiteral) as ?ehEquals)
          BIND (geof:ehEquals(?aLiteral, ?bLiteral) as ?ehEquals2)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["equals"]) == "true"
            assert str(result[0]["equals2"]) == "false"
    
    
    def test_ehContains(self):
        resultlist=TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?ehContains) as ?contains)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:F geo:hasDefaultGeometry ?fGeom .
          ?fGeom %%literalrel2%% ?fLiteral .
          BIND (geof:ehContains(?aLiteral, ?fLiteral) as ?ehContains)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["contains"]) == "true"
    
    def test_ehCovers(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?ehCovers) as ?covers)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:B geo:hasDefaultGeometry ?bGeom .
          ?bGeom %%literalrel2%% ?bLiteral .
          BIND (geof:ehCovers(?aLiteral, ?bLiteral) as ?ehCovers)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["covers"]) == "true"
    
    def test_ehCoveredBy(self):
        resultlist=TestUtils.queryExecution("""
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?ehCoveredBy) as ?coveredBy)
        WHERE {
          my:B geo:hasDefaultGeometry ?bGeom .
          ?bGeom %%literalrel1%% ?bLiteral .
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel2%% ?aLiteral .
          BIND (geof:ehCoveredBy(?bLiteral, ?aLiteral) as ?ehCoveredBy)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["coveredBy"]) == "true"
    
    def test_ehDisjoint(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?ehDisjoint) as ?disjoint) (xsd:boolean(?ehDisjoint2) as ?disjoint2)
        WHERE {
          my:B geo:hasDefaultGeometry ?bGeom .
          ?bGeom %%literalrel1%% ?bLiteral .
          my:C geo:hasDefaultGeometry ?cGeom .
          ?cGeom %%literalrel2%% ?cLiteral .
          BIND (geof:ehDisjoint(?bLiteral, ?bLiteral) as ?ehDisjoint)
          BIND (geof:ehDisjoint(?bLiteral, ?cLiteral) as ?ehDisjoint2)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["disjoint"]) == "false"
            assert str(result[0]["disjoint2"]) == "true"
    
    def test_ehInside(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?insidee) as ?inside)
        WHERE {
          my:F geo:hasDefaultGeometry ?fGeom .
          ?fGeom %%literalrel1%% ?fLiteral .
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel2%% ?aLiteral .
          BIND (geof:ehInside(?fLiteral, ?aLiteral) as ?insidee)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["inside"]) == "true"
    
    def test_ehMeet(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?ehMeet) as ?meet)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:C geo:hasDefaultGeometry ?cGeom .
          ?cGeom %%literalrel2%% ?cLiteral .
          BIND (geof:ehMeet(?aLiteral, ?cLiteral) as ?ehMeet)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["meet"]) == "true"
    
    def test_ehOverlap(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?ehOverlap) as ?overlap)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom %%literalrel2%% ?dLiteral .
          BIND (geof:ehOverlap(?aLiteral, ?dLiteral) as ?ehOverlap)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["overlap"]) == "true"
    
    def test_geometryType(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        SELECT ?gtype
        WHERE {
          my:A geo:hasDefaultGeometry ?geom .
          ?geom %%literalrel1%% ?literal .
          BIND (geof:geometryType(?literal) as ?gtype)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["gtype"]) == "Polygon"

    def test_getSRID(self):
        result = g.query(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?srid
            WHERE {
              my:A geo:hasDefaultGeometry ?geom .
              ?geom geo:asWKT ?literal .
              BIND (geof:getSRID(?literal) as ?srid)
            }
            """)
        result = [{str(k): v for k, v in i.items()} for i in result.bindings]
        assert len(result) == 1
        assert str(result[0]["srid"]) == "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
    
    def test_intersection(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?intersection
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom %%literalrel2%% ?dLiteral .
          BIND (geof:intersection(?aLiteral, ?dLiteral) as ?intersection)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((-83.2 34.1, -83.3 34.1, -83.3 34.2, -83.2 34.2, -83.2 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["intersection"])[0],expresult,tolerance=eqtolerance)


    def test_rcc8eq(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?rcc8eq) as ?equals) (xsd:boolean(?rcc8eq2) as ?equals2)
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              my:B geo:hasDefaultGeometry ?bGeom .
              ?bGeom %%literalrel2%% ?bLiteral .
              BIND (geof:rcc8eq(?aLiteral, ?aLiteral) as ?rcc8eq)
              BIND (geof:rcc8eq(?aLiteral, ?bLiteral) as ?rcc8eq2)
            }
            """, combinations, config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["equals"]) == "true"
            assert str(result[0]["equals2"]) == "false"

    def test_rcc8ec(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?sfTouches) as ?touches)
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              my:C geo:hasDefaultGeometry ?cGeom .
              ?cGeom %%literalrel2%% ?cLiteral .
              BIND (geof:rcc8ec(?aLiteral, ?cLiteral) as ?sfTouches)
            }
            """, combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["touches"]) == "true"

    def test_rcc8dc(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?rcc8dc) as ?disjoint) (xsd:boolean(?rcc8dc2) as ?disjoint2)
            WHERE {
              my:B geo:hasDefaultGeometry ?bGeom .
              ?bGeom %%literalrel1%% ?bLiteral .
              my:C geo:hasDefaultGeometry ?cGeom .
              ?cGeom %%literalrel2%% ?cLiteral .
              BIND (geof:rcc8dc(?bLiteral, ?bLiteral) as ?rcc8dc)
              BIND (geof:rcc8dc(?bLiteral, ?cLiteral) as ?rcc8dc2)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["disjoint"]) == "false"
            assert str(result[0]["disjoint2"]) == "true"

    def test_rcc8ntpp(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?rcc8ntppr) as ?rcc8ntpp) (xsd:boolean(?rcc8ntppr2) as ?rcc8ntpp2)
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              my:G geo:hasDefaultGeometry ?gGeom .
              ?gGeom %%literalrel2%% ?gLiteral .
              BIND (geof:rcc8ntpp(?gLiteral, ?aLiteral) as ?rcc8ntppr)
              BIND (geof:rcc8ntpp(?aLiteral, ?gLiteral) as ?rcc8ntppr2)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["rcc8ntpp"]) == "true"
            assert str(result[0]["rcc8ntpp2"]) == "false"

    def test_rcc8ntppi(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?rcc8ntppir) as ?rcc8ntppi) (xsd:boolean(?rcc8ntppir2) as ?rcc8ntppi2)
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              my:G geo:hasDefaultGeometry ?gGeom .
              ?gGeom %%literalrel2%% ?gLiteral .
              BIND (geof:rcc8ntppi(?aLiteral, ?gLiteral) as ?rcc8ntppir)
              BIND (geof:rcc8ntppi(?gLiteral, ?aLiteral) as ?rcc8ntppir2)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["rcc8ntppi"]) == "true"
            assert str(result[0]["rcc8ntppi2"]) == "false"

    def test_rcc8po(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?rcc8por) as ?rcc8po)
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              my:D geo:hasDefaultGeometry ?dGeom .
              ?dGeom %%literalrel2%% ?dLiteral .
              BIND (geof:rcc8po(?aLiteral, ?dLiteral) as ?rcc8por)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["rcc8po"]) == "true"

    def test_rcc8tpp(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?rcc8tppr) as ?rcc8tpp)
            WHERE {
              my:B geo:hasDefaultGeometry ?bGeom .
              ?aGeom %%literalrel1%% ?bLiteral .
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel2%% ?aLiteral .
              BIND (geof:rcc8tpp(?aLiteral, ?bLiteral) as ?rcc8tppr)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["rcc8tpp"]) == "true"

    def test_rcc8tppi(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT (xsd:boolean(?rcc8tppir) as ?rcc8tppi)
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              my:B geo:hasDefaultGeometry ?bGeom .
              ?bGeom %%literalrel2%% ?bLiteral .
              BIND (geof:rcc8tppi(?aLiteral, ?bLiteral) as ?rcc8tppir)
            }
            """, combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert str(result[0]["rcc8tppi"]) == "true"

    def test_relate(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?relate) as ?relates) (xsd:boolean(?relate2) as ?relates2)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:B geo:hasDefaultGeometry ?bGeom .
          ?bGeom %%literalrel2%% ?bLiteral .
          # "T*****FF*" refers to a 'contains' relation in DE-9IM
          BIND (geof:relate(?aLiteral, ?bLiteral, "T*****FF*"^^xsd:string) as ?relate)
          BIND (geof:relate(?aLiteral, ?bLiteral, "F*****FF*"^^xsd:string) as ?relate2)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["relates"]) == "true"
            assert str(result[0]["relates2"]) == "false"

    def test_sfCrosses(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfCrosses) as ?crosses)
        WHERE {
          my:E geo:hasDefaultGeometry ?eGeom .
          ?eGeom %%literalrel1%% ?eLiteral .
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel2%% ?aLiteral .
          BIND (geof:sfCrosses(?eLiteral, ?aLiteral) as ?sfCrosses)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["crosses"]) == "true"

    def test_sfContains(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfContains) as ?contains)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:F geo:hasDefaultGeometry ?fGeom .
          ?fGeom %%literalrel2%% ?fLiteral .
          BIND (geof:sfContains(?aLiteral, ?fLiteral) as ?sfContains)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["contains"]) == "true"


    def test_sfDisjoint(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfDisjoint) as ?disjoint)
        WHERE {
          my:C geo:hasDefaultGeometry ?cGeom .
          ?cGeom %%literalrel1%% ?cLiteral .
          my:F geo:hasDefaultGeometry ?fGeom .
          ?fGeom %%literalrel2%% ?fLiteral .
          BIND (geof:sfDisjoint(?cLiteral, ?fLiteral) as ?sfDisjoint)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["disjoint"]) == "true"


    def test_sfEquals(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfEquals) as ?equals) (xsd:boolean(?sfEquals2) as ?equals2)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:B geo:hasDefaultGeometry ?bGeom .
          ?bGeom %%literalrel2%% ?bLiteral .
          BIND (geof:sfEquals(?aLiteral, ?aLiteral) as ?sfEquals)
          BIND (geof:sfEquals(?aLiteral, ?bLiteral) as ?sfEquals2)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["equals"]) == "true"
            assert str(result[0]["equals2"]) == "false"

    def test_sfIntersects(self):
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
          BIND (geof:sfIntersects(?aLiteral, ?dLiteral) as ?sfIntersects)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["intersects"]) == "true"


    def test_sfTouches(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfTouches) as ?touches)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:C geo:hasDefaultGeometry ?cGeom .
          ?cGeom %%literalrel2%% ?cLiteral .
          BIND (geof:sfTouches(?aLiteral, ?cLiteral) as ?sfTouches)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["touches"]) == "true"

    def test_sfWithin(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfWithin) as ?within)
        WHERE {
          my:B geo:hasDefaultGeometry ?bGeom .
          ?bGeom %%literalrel1%% ?bLiteral .
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel2%% ?aLiteral .
          BIND (geof:sfWithin(?bLiteral, ?aLiteral) as ?sfWithin)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["within"]) == "true"

    def test_sfOverlaps(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT (xsd:boolean(?sfOverlaps) as ?overlaps)
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom %%literalrel2%% ?dLiteral .
          BIND (geof:sfOverlaps(?aLiteral, ?dLiteral) as ?sfOverlaps)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["overlaps"]) == "true"
    
    def test_symDifference(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?sdifference
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom %%literalrel2%% ?dLiteral .
          BIND (geof:symDifference(?aLiteral, ?dLiteral) as ?sdifference)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("MULTIPOLYGON (((-83.6 34.1, -83.6 34.5, -83.2 34.5, -83.2 34.2, -83.3 34.2, -83.3 34.1, -83.6 34.1)), ((-83.2 34.1, -83.2 34.2, -83.1 34.2, -83.1 34, -83.3 34, -83.3 34.1, -83.2 34.1)))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["sdifference"])[0],expresult,tolerance=eqtolerance)
    
    def test_union(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?union
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          my:D geo:hasDefaultGeometry ?dGeom .
          ?dGeom %%literalrel2%% ?dLiteral .
          BIND (geof:union(?aLiteral, ?dLiteral) as ?union)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((-83.6 34.1, -83.6 34.5, -83.2 34.5, -83.2 34.2, -83.1 34.2, -83.1 34, -83.3 34, -83.3 34.1, -83.6 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["union"])[0],expresult,tolerance=eqtolerance)