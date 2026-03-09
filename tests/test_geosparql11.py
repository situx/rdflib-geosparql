import shapely.geometry
from rdflib import Graph, Namespace
import os
import itertools
from shapely.testing import assert_geometries_equal
from geosparql.geosparql import LiteralUtils
from test_geosparql10 import TestGeoSPARQL10
from testutils import TestUtils

GEO = Namespace("http://www.opengis.net/ont/geosparql#")
GEOF = Namespace("http://www.opengis.net/def/function/geosparql/")
GEOFEXT = Namespace("http://www.opengis.net/def/function/geosparql/ext/")
GEOPREFIX="geo:"
GEOFPREFIX="geof:"
GEOFEXTPREFIX="geofext:"
eqtolerance=1e-1


g = Graph()
dir_path = os.path.dirname(os.path.realpath(__file__))
g.parse(dir_path+"/testdata.ttl")
config={
    "literalTypes":{
        "WKT":"geo:wktLiteral",
        "GML":"geo:gmlLiteral",
        "GeoJSON":"geo:geoJSONLiteral",
        "KML":"geo:kmlLiteral",
        #"DGGS":"geo:dggsLiteral"
    },
    "geoProperties":{
        "WKT":"geo:asWKT",
        "GML":"geo:asGML",
        "GeoJSON":"geo:asGeoJSON",
        "KML":"geo:asKML",
        #"DGGS":"geo:asDGGS"
    }
}
combinations=list(itertools.permutations(config["geoProperties"],2))
combinations = list(map(lambda x, y: (x, y), config["literalTypes"].keys(), config["literalTypes"].keys())) + combinations
print(combinations)

class TestGeoSPARQL11(TestGeoSPARQL10):

    def test_area(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?area
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:area(?aLiteral) as ?area)
            }
            """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result[0]) == 1
            assert "area" in result[0] and str(result[0]["area"]) == "0.15999999999999603"

    def test_asWKT(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?wkt
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:asWKT(?aLiteral) as ?wkt)
        }
        """,combinations,config, g)
        expresult=shapely.from_wkt("POLYGON ((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))")
        for res in resultlist:
            print("Testing with "+str(res[1]))
            result=res[0]
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["wkt"])[0],expresult,tolerance=eqtolerance)

    def test_asGeoJSON(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?geojson
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:asGeoJSON(?aLiteral) as ?geojson)
        }
        """,combinations,config, g)
        expresult=shapely.from_wkt("Polygon((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["geojson"])[0],expresult,tolerance=eqtolerance)
            #assert str(result[0]["geojson"]) == "{\"type\":\"Polygon\",\"coordinates\":[[[-83.6,34.1],[-83.2,34.1],[-83.2,34.5],[-83.6,34.5],[-83.6,34.1]]]}"

    def test_asGML(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?gml
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:asGML(?aLiteral) as ?gml)
        }
        """,combinations,config, g)
        expresult=shapely.from_wkt("Polygon((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["gml"])[0],expresult,tolerance=eqtolerance)

    def test_asKML(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?kml
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:asKML(?aLiteral) as ?kml)
        }
        """,combinations,config, g)
        expresult=shapely.from_wkt("Polygon((-83.6 34.1, -83.2 34.1, -83.2 34.5, -83.6 34.5, -83.6 34.1))")
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["kml"])[0],expresult,tolerance=eqtolerance)

    def test_asDGGS(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX geof: <"""+str(GEOF)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?kml
        WHERE {
          my:A geo:hasDefaultGeometry ?aGeom .
          ?aGeom %%literalrel1%% ?aLiteral .
          BIND (geof:asDGGS(?aLiteral,"https://h3geo.org/res/7") as ?kml)
        }
        """,combinations,config, g)
        expresult="<https://h3geo.org/res/7> CELLLIST('8744c3328ffffff', '8744cec36ffffff', '8744c330dffffff', '8744cec1bffffff', '8744ced30ffffff', '8744ce5a6ffffff', '8744cec12ffffff', '8744ced1effffff', '8744ced15ffffff', '8744cec00ffffff', '8744c3a58ffffff', '8744cecf1ffffff', '8744cecd6ffffff', '8744cecc4ffffff', '8744ce531ffffff', '8744cecb2ffffff', '8744ceca9ffffff', '8744cedb5ffffff', '8744c3343ffffff', '8744c3acdffffff', '8744c3274ffffff', '8744ceca0ffffff', '8744ce516ffffff', '8744c326bffffff', '8744c334cffffff', '8744cedacffffff', '8744ceda3ffffff', '8744c3262ffffff', '8744cec8effffff', '8744c3240ffffff', '8744c3355ffffff', '8744ced81ffffff', '8744ce504ffffff', '8744ced9affffff', '8744c336effffff', '8744c3249ffffff', '8744c335effffff', '8744ced8affffff', '8744c3259ffffff', '8744cec85ffffff', '8744c3365ffffff', '8744ced93ffffff', '8744ced91ffffff', '8744c335cffffff', '8744ced88ffffff', '8744c3addffffff', '8744c3353ffffff', '8744c325bffffff', '8744c3370ffffff', '8744ced9cffffff', '8744c334affffff', '8744ce506ffffff', '8744cec90ffffff', '8744ceda5ffffff', '8744c3264ffffff', '8744c3acbffffff', '8744c3341ffffff', '8744cec34ffffff', '8744cec99ffffff', '8744cedaeffffff', '8744c326dffffff', '8744cec22ffffff', '8744cec19ffffff', '8744ce5a4ffffff', '8744ceca2ffffff', '8744cec10ffffff', '8744ced1cffffff', '8744ced13ffffff', '8744c3a4dffffff', '8744ce521ffffff', '8744cecabffffff', '8744cece6ffffff', '8744cecd4ffffff', '8744cecc2ffffff', '8744cecb0ffffff', '8744ce526ffffff', '8744cecb4ffffff', '8744cedb3ffffff', '8744cec9effffff', '8744ce514ffffff', '8744cedaaffffff', '8744ce533ffffff', '8744c3269ffffff', '8744cec95ffffff', '8744ceda1ffffff', '8744c3375ffffff', '8744c3260ffffff', '8744cec8cffffff', '8744cecc6ffffff', '8744c336cffffff', '8744ced98ffffff', '8744cec83ffffff', '8744c3363ffffff', '8744c324effffff', '8744ced86ffffff', '8744c335affffff', '8744c3245ffffff', '8744c3adbffffff', '8744c3351ffffff', '8744c3348ffffff', '8744c3ac9ffffff', '8744c332dffffff', '8744cec32ffffff', '8744c3309ffffff', '8744ce5a2ffffff', '8744cec0effffff', '8744cece1ffffff', '8744ced1affffff', '8744ced11ffffff', '8744c3a5dffffff', '8744cecf6ffffff', '8744c3a4bffffff', '8744ceceaffffff', '8744cece4ffffff', '8744c3a48ffffff', '8744cecd2ffffff', '8744cecc0ffffff', '8744ce536ffffff', '8744cecf3ffffff', '8744ce52dffffff', '8744cecaeffffff', '8744ce524ffffff', '8744ceca5ffffff', '8744cedb1ffffff', '8744c3270ffffff', '8744cec9cffffff', '8744c3a5affffff', '8744ce512ffffff', '8744ceda8ffffff', '8744cec93ffffff', '8744c3373ffffff', '8744cec8affffff', '8744ce500ffffff', '8744c336affffff', '8744ced96ffffff', '8744c3255ffffff', '8744cec81ffffff', '8744c3361ffffff', '8744c3aebffffff', '8744ced8dffffff', '8744c324cffffff', '8744cec02ffffff', '8744ced84ffffff', '8744c3358ffffff', '8744c3243ffffff', '8744c3ad9ffffff', '8744c3346ffffff', '8744c332bffffff', '8744cec30ffffff', '8744ced33ffffff', '8744cec1effffff', '8744cec15ffffff', '8744ce5a0ffffff', '8744cec14ffffff', '8744ced18ffffff', '8744cec03ffffff', '8744c3a5bffffff', '8744cecf4ffffff', '8744c3a49ffffff', '8744cec1dffffff', '8744ced32ffffff', '8744cecebffffff', '8744cece2ffffff', '8744cecd0ffffff', '8744ce534ffffff', '8744cec26ffffff', '8744cecb5ffffff', '8744cecacffffff', '8744ce522ffffff', '8744ceca3ffffff', '8744c326effffff', '8744cec9affffff', '8744ce510ffffff', '8744c3265ffffff', '8744ceda6ffffff', '8744cec91ffffff', '8744ced9dffffff', '8744c3371ffffff', '8744c325cffffff', '8744cec88ffffff', '8744c3368ffffff', '8744ced94ffffff', '8744c3ae9ffffff', '8744ced8bffffff', '8744c324affffff', '8744c332affffff', '8744ced82ffffff', '8744c3356ffffff', '8744c3241ffffff', '8744c334dffffff', '8744c3aceffffff', '8744c3344ffffff', '8744c3329ffffff', '8744cec1cffffff', '8744cec13ffffff', '8744cec0affffff', '8744ced16ffffff', '8744cec01ffffff', '8744c3a59ffffff', '8744cecf2ffffff', '8744cece0ffffff', '8744cecc5ffffff', '8744ce532ffffff', '8744c3345ffffff', '8744cecb3ffffff', '8744cecaaffffff', '8744ce520ffffff', '8744c3275ffffff', '8744cedb6ffffff', '8744c334effffff', '8744c3ad8ffffff', '8744ceca1ffffff', '8744c326cffffff', '8744cedadffffff', '8744c3242ffffff', '8744ced83ffffff', '8744cec98ffffff', '8744c3263ffffff', '8744ceda4ffffff', '8744ce505ffffff', '8744c324bffffff', '8744c3360ffffff', '8744c3aeaffffff', '8744ced8cffffff', '8744ced9bffffff', '8744cec80ffffff', '8744ced95ffffff', '8744c3369ffffff', '8744cec86ffffff', '8744c3366ffffff', '8744ced92ffffff', '8744cec89ffffff', '8744c325dffffff', '8744c3372ffffff', '8744ced9effffff', '8744ced89ffffff', '8744c335dffffff', '8744cec92ffffff', '8744c3266ffffff', '8744c3248ffffff', '8744c3adeffffff', '8744c3354ffffff', '8744ced80ffffff', '8744cec9bffffff', '8744cedb0ffffff', '8744c334bffffff', '8744c3accffffff', '8744c3342ffffff', '8744c322dffffff', '8744ceca4ffffff', '8744c3ac3ffffff', '8744cec35ffffff', '8744cec1affffff', '8744ce5a5ffffff', '8744ce523ffffff', '8744cecadffffff', '8744cec11ffffff', '8744ced14ffffff', '8744ced02ffffff', '8744cecf0ffffff', '8744ce52cffffff', '8744cecb6ffffff', '8744cecdeffffff', '8744cecd5ffffff', '8744cecccffffff', '8744cecc3ffffff', '8744ce535ffffff', '8744ce530ffffff', '8744cecb1ffffff', '8744ceca8ffffff', '8744c3273ffffff', '8744cedb4ffffff', '8744ce515ffffff', '8744cedabffffff', '8744c326affffff', '8744cec96ffffff', '8744c3261ffffff', '8744c3376ffffff', '8744ceda2ffffff', '8744cecd1ffffff', '8744cec8dffffff', '8744ced99ffffff', '8744c336dffffff', '8744c3258ffffff', '8744cec84ffffff', '8744c3364ffffff', '8744ced90ffffff', '8744c335bffffff', '8744c3246ffffff', '8744c3adcffffff', '8744c3ad3ffffff', '8744cece3ffffff', '8744c3349ffffff', '8744c3acaffffff', '8744c3340ffffff', '8744c3ac1ffffff', '8744c332effffff', '8744cec33ffffff', '8744ced36ffffff', '8744c3a4affffff', '8744cec18ffffff', '8744ced1bffffff', '8744cec06ffffff', '8744cecf5ffffff', '8744ced12ffffff', '8744ceceeffffff', '8744cece5ffffff', '8744cecdcffffff', '8744cecd3ffffff', '8744cecc1ffffff', '8744ce52effffff', '8744ce525ffffff', '8744ceca6ffffff', '8744cedb2ffffff', '8744c3271ffffff', '8744cec9dffffff', '8744c3268ffffff', '8744ceda9ffffff', '8744cec94ffffff', '8744c3374ffffff', '8744ceda0ffffff', '8744ced10ffffff', '8744cec8bffffff', '8744c336bffffff', '8744cec82ffffff', '8744ced8effffff', '8744cec04ffffff', '8744c3362ffffff', '8744c324dffffff', '8744ced85ffffff', '8744c3359ffffff', '8744c3244ffffff', '8744c3adaffffff', '8744c3350ffffff', '8744c3ad1ffffff', '8744c3ac8ffffff', '8744c3229ffffff', '8744c332cffffff', '8744cec16ffffff', '8744cec31ffffff')"
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert str(result[0]["kml"])==expresult


    def test_boundingCircle(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?bcirc
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:boundingCircle(?aLiteral) as ?bcirc)
            }
            """,combinations,config,g)
        expresult = shapely.from_wkt("""POLYGON ((-83.1171572875254 34.3, -83.12259203093559 34.24482012414341, -83.13868740702475 34.191760779970764, -83.16482487951615 34.14286100832258, -83.20000000000002 34.10000000000001, -83.24286100832259 34.06482487951614, -83.29176077997077 34.03868740702473, -83.34482012414342 34.02259203093558, -83.4 34.017157287525386, -83.45517987585659 34.02259203093558, -83.50823922002924 34.03868740702473, -83.55713899167742 34.06482487951614, -83.6 34.1, -83.63517512048386 34.14286100832258, -83.66131259297526 34.191760779970764, -83.67740796906442 34.24482012414341, -83.68284271247461 34.3, -83.67740796906442 34.355179875856585, -83.66131259297526 34.40823922002923, -83.63517512048386 34.45713899167741, -83.6 34.499999999999986, -83.55713899167742 34.535175120483856, -83.50823922002924 34.56131259297526, -83.45517987585659 34.57740796906442, -83.4 34.58284271247461, -83.34482012414342 34.57740796906442, -83.29176077997077 34.56131259297526, -83.24286100832259 34.535175120483856, -83.20000000000002 34.49999999999999, -83.16482487951615 34.45713899167741, -83.13868740702475 34.40823922002923, -83.12259203093559 34.355179875856585, -83.1171572875254 34.3))""")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["bcirc"])[0], expresult)

    def test_centroid(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?centroid
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:centroid(?aLiteral) as ?centroid)
            }
            """,combinations,config,g)
        expresult = shapely.from_wkt("POINT (-83.39999999999999 34.300000000000004)")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["centroid"])[0], expresult)

    def test_concaveHull(self):
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
              BIND (geof:concaveHull(?aLiteral) as ?chull)
            }
            """,combinations,config,g)
        expresult = shapely.from_wkt("POLYGON ((-83.2 34.1, -83.6 34.1, -83.6 34.5, -83.2 34.5, -83.2 34.1))")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["chull"])[0], expresult)

    def test_coordinateDimension(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?coordinateDimension
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:coordinateDimension(?literal) AS ?coordinateDimension)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "coordinateDimension" in result[0] and str(result[0]["coordinateDimension"]) == "2"


    def test_geometryN(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?geomN
            WHERE {
              BIND(geof:geometryN("MULTIPOLYGON (((1 1, 1 3, 3 3, 3 1, 1 1)), ((4 3, 6 3, 6 1, 4 1, 4 3)))"^^geo:wktLiteral,"1"^^xsd:integer) AS ?geomN)
            }
            """,combinations,config,g)
        expresult = shapely.from_wkt("POLYGON ((4 3, 6 3, 6 1, 4 1, 4 3))")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["geomN"])[0], expresult)

    def test_is3D(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
                PREFIX geof: <"""+str(GEOF)+""">
                SELECT ?isN3D ?isK3D {
                    <http://example.org/ApplicationSchema#NExactGeom> %%literalrel1%% ?n_wkt .
                    BIND(geof:is3D(?n_wkt) AS ?isN3D)
                            <http://example.org/ApplicationSchema#KExactGeom> %%literalrel1%% ?k_wkt .
                    BIND(geof:is3D(?k_wkt) AS ?isK3D)
                }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "isN3D" in result[0] and str(result[0]["isN3D"]) == "true"
            assert "isK3D" in result[0] and str(result[0]["isK3D"]) == "false"


    def test_isEmpty(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
               PREFIX geof: <"""+str(GEOF)+""">
               PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
               SELECT (xsd:boolean(?isIEmptyr) as ?isIEmpty) (xsd:boolean(?isKEmptyr) as ?isKEmpty) {
                    <http://example.org/ApplicationSchema#IExactGeom> %%literalrel1%% ?i_wkt .
                    BIND(geof:isEmpty(?i_wkt) AS ?isIEmptyr)
                     <http://example.org/ApplicationSchema#KExactGeom> %%literalrel2%% ?k_wkt .
                    BIND(geof:isEmpty(?k_wkt) AS ?isKEmptyr)
                }
            """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "isIEmpty" in result[0] and str(result[0]["isIEmpty"]) == "true"
            assert "isKEmpty" in result[0] and str(result[0]["isKEmpty"]) == "false"

    def test_isMeasured(self):
        resultlist = TestUtils.queryExecution(
        """PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?isEMeasured ?isLMeasured {
                BIND(geof:isMeasured("POINT (1 2)"^^geo:wktLiteral) AS ?isEMeasured)
                BIND(geof:isMeasured("POINT M (1 2 3)"^^geo:wktLiteral) AS ?isLMeasured)
            }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert "isLMeasured" in result[0] and str(result[0]["isLMeasured"]) == "true"
            assert "isEMeasured" in result[0] and str(result[0]["isEMeasured"]) == "false"

    def test_isSimple(self):
        resultlist = TestUtils.queryExecution(
            """PREFIX geo: <"""+str(GEO)+""">
                PREFIX geof: <"""+str(GEOF)+""">
                SELECT ?isASimple ?isOSimple {
                    <http://example.org/ApplicationSchema#AExactGeom> %%literalrel1%% ?a_wkt .
                    BIND(geof:isSimple(?a_wkt) AS ?isASimple)
                    <http://example.org/ApplicationSchema#OExactGeom> %%literalrel1%% ?o_wkt .
                    BIND(geof:isSimple(?o_wkt) AS ?isOSimple)
                }
            """, combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "isASimple" in result[0] and str(result[0]["isASimple"]) == "true"
            assert "isOSimple" in result[0] and str(result[0]["isOSimple"]) == "false"

    def test_length(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?length
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:length(?aLiteral) as ?length)
            }
            """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "length" in result[0] and str(result[0]["length"]) == "1.59999999999998"

    def test_metricArea(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?marea
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:metricArea(?aLiteral) as ?marea)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result[0]) == 1
            assert "marea" in result[0] and str(result[0]["marea"]) == "2400116828.6431704"

    def test_metricBuffer(self):
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
              BIND (geof:metricBuffer(?aLiteral,"5.0"^^xsd:double) as ?buffer)
            }
            """,combinations,config,g)
        expresult = shapely.from_wkt(
            """POLYGON ((-9306314.43031767 4042237.4996761675, -9306314.43031767 4096139.0404472337, -9306314.334244072 4096140.0158988438, -9306314.049715333 4096140.9538643956, -9306313.587665731 4096141.818298399, -9306312.965851575 4096142.5759811397, -9306312.208168834 4096143.197795295, -9306311.343734832 4096143.6598448963, -9306310.405769281 4096143.9443736356, -9306309.43031767 4096144.0404472337, -9261781.634000361 4096144.0404472337, -9261780.65854875 4096143.9443736356, -9261779.720583199 4096143.6598448963, -9261778.856149197 4096143.197795295, -9261778.098466456 4096142.5759811397, -9261777.4766523 4096141.818298399, -9261777.014602698 4096140.9538643956, -9261776.730073959 4096140.0158988438, -9261776.634000361 4096139.0404472337, -9261776.634000361 4042237.4996761675, -9261776.730073959 4042236.5242245574, -9261777.014602698 4042235.5862590056, -9261777.4766523 4042234.721825002, -9261778.098466456 4042233.9641422615, -9261778.856149197 4042233.342328106, -9261779.720583199 4042232.880278505, -9261780.65854875 4042232.5957497656, -9261781.634000361 4042232.4996761675, -9306309.43031767 4042232.4996761675, -9306310.405769281 4042232.5957497656, -9306311.343734832 4042232.880278505, -9306312.208168834 4042233.342328106, -9306312.965851575 4042233.9641422615, -9306313.587665731 4042234.721825002, -9306314.049715333 4042235.5862590056, -9306314.334244072 4042236.5242245574, -9306314.43031767 4042237.4996761675))""")
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["buffer"])[0], expresult)

    def test_metricDistance(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?mdistance
            WHERE {
              my:C geo:hasDefaultGeometry ?cGeom .
              ?cGeom %%literalrel1%% ?cLiteral .
              my:F geo:hasDefaultGeometry ?fGeom .
              ?fGeom %%literalrel2%% ?fLiteral .
              BIND (geof:metricDistance(?cLiteral, ?fLiteral) as ?mdistance)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "mdistance" in result[0] and str(result[0]["mdistance"]) == "22263.89815865457"

    def test_metricLength(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?mlength
            WHERE {
              my:A geo:hasDefaultGeometry ?aGeom .
              ?aGeom %%literalrel1%% ?aLiteral .
              BIND (geof:metricLength(?aLiteral) as ?mlength)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "mlength" in result[0] and str(result[0]["mlength"]) == "196858.6741767507"

    def test_metricPerimeter(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?mperimeter
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:metricPerimeter(?literal) AS ?mperimeter)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "mperimeter" in result[0] and str(result[0]["mperimeter"]) == "196858.6741767507"

    def test_maxX(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?maxX
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:maxX(?literal) AS ?maxX)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "maxX" in result[0] and str(result[0]["maxX"]) == "-83.2"

    def test_maxY(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?maxY
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:maxY(?literal) AS ?maxY)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "maxY" in result[0] and str(result[0]["maxY"]) == "34.5"

    def test_maxZ(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?maxZ
            WHERE {
              my:NExactGeom %%literalrel1%% ?literal .
              BIND(geof:maxZ(?literal) AS ?maxZ)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "maxZ" in result[0] and str(result[0]["maxZ"]) == "2.0"
        

    def test_minX(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?minX
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:minX(?literal) AS ?minX)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "minX" in result[0] and str(result[0]["minX"]) == "-83.6"

    def test_minY(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?minY
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:minY(?literal) AS ?minY)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "minY" in result[0] and str(result[0]["minY"]) == "34.1"

    def test_minZ(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?minZ
            WHERE {
              my:NExactGeom %%literalrel1%% ?literal .
              BIND(geof:minZ(?literal) AS ?minZ)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "minZ" in result[0] and str(result[0]["minZ"]) == "1.0"

    def test_numGeometries(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?numGeoms
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:numGeometries(?literal) AS ?numGeoms)
            }
            """,combinations,config,g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "numGeoms" in result[0] and str(result[0]["numGeoms"]) == "1"

    def test_perimeter(self):
        resultlist = TestUtils.queryExecution(
            """
            PREFIX my: <http://example.org/ApplicationSchema#>
            PREFIX geo: <"""+str(GEO)+""">
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geof: <"""+str(GEOF)+""">
            SELECT ?perimeter
            WHERE {
              my:AExactGeom %%literalrel1%% ?literal .
              BIND(geof:perimeter(?literal) AS ?perimeter)
            }
            """,combinations,config, g)
        for res in resultlist:
            result = res[0]
            print("Testing with " + str(res[1]))
            assert len(result) == 1
            assert "perimeter" in result[0] and str(result[0]["perimeter"]) == "1.59999999999998"

    def test_spatialDimension(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX geof: <"""+str(GEOF)+""">
        SELECT ?spatialDimension
        WHERE {
          my:AExactGeom %%literalrel1%% ?literal .
          BIND(geof:spatialDimension(?literal) AS ?spatialDimension)
        }
        """,combinations,config,g)
        for res in resultlist:
            result=res[0]
            print("Testing with "+str(res[1]))
            assert len(result) == 1
            assert "spatialDimension" in result[0] and str(result[0]["spatialDimension"]) == "2"

    def test_transform(self):
        resultlist = TestUtils.queryExecution(
        """
        PREFIX my: <http://example.org/ApplicationSchema#>
        PREFIX geo: <"""+str(GEO)+""">
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX geof: <"""+str(GEOF)+""">
        SELECT ?transformed
        WHERE {
          my:AExactGeom %%literalrel1%% ?literal .
          BIND(geof:transform(?literal,"http://www.opengis.net/def/crs/EPSG/0/4326") AS ?transformed)
        }
        """,combinations,config,g)
        expresult=shapely.from_wkt("POLYGON ((34.1 -83.6, 34.1 -83.2, 34.5 -83.2, 34.5 -83.6, 34.1 -83.6))")
        for res in resultlist:
            print("Testing with "+str(res[1]))
            result=res[0]
            assert len(result) == 1
            if "transformed" in result[0]:
                assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result[0]["transformed"])[0],expresult,tolerance=eqtolerance)
            else:
                assert_geometries_equal(LiteralUtils.processLiteralTypeToGeom(result)[0], expresult)
