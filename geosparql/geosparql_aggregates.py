from rdflib.plugins.sparql.aggregates import Accumulator, Aggregator, type_safe_numbers
from rdflib.plugins.sparql.parserutils import CompValue
from rdflib.plugins.sparql.operators import numeric
from rdflib.plugins.sparql.datatypes import type_promotion
from rdflib.plugins.sparql.sparql import FrozenBindings, NotBoundError, SPARQLTypeError
from rdflib.plugins.sparql.evalutils import _eval, _val
from rdflib import Literal

import shapely
from fastkml import kml

def processLiteralTypeToGeom(literal):
    if not isinstance(literal,Literal):
        raise ValueError(
            "The "+str(literal)+" is not a literal!"
        )
    dtype=str(literal.datatype)
    if dtype=="http://www.opengis.net/ont/geosparql#wktLiteral":
        lstring=str(literal).strip()
        if lstring.startswith("<"):
            srsuri=lstring[0:lstring.find(">")].replace("<","").replace(">","")
            return shapely.from_wkt(lstring[lstring.find(">")+1:])
        else:
            return shapely.from_wkt(str(literal))
    elif dtype == "http://www.opengis.net/ont/geosparql#wkbLiteral":
        return shapely.from_wkb(str(literal))
    elif dtype == "http://www.opengis.net/ont/geosparql#geoJSONLiteral":
        return shapely.from_geojson(str(literal))
    elif dtype == "http://www.opengis.net/ont/geosparql#kmlLiteral":
        return kml.KML.from_string(str(literal))
    else:
        thelit=str(literal)
        if len(thelit)>100:
            thelit=thelit[0:100]
        raise ValueError(
            "The literal "+thelit+" ("+str(literal.datatype)+") is no known geometry literal type!"
        )

def processLiteralTypeToGeom(literal):
    if not isinstance(literal,Literal):
        raise ValueError(
            "The "+str(literal)+" is not a literal!"
        )
    dtype=str(literal.datatype)
    if dtype=="http://www.opengis.net/ont/geosparql#wktLiteral":
        lstring=str(literal).strip()
        if lstring.startswith("<"):
            srsuri=lstring[0:lstring.find(">")].replace("<","").replace(">","")
            return shapely.from_wkt(lstring[lstring.find(">")+1:])
        else:
            return shapely.from_wkt(str(literal))
    elif dtype == "http://www.opengis.net/ont/geosparql#wkbLiteral":
        return shapely.from_wkb(str(literal))
    elif dtype == "http://www.opengis.net/ont/geosparql#geoJSONLiteral":
        return shapely.from_geojson(str(literal))
    elif dtype == "http://www.opengis.net/ont/geosparql#kmlLiteral":
        return kml.KML.from_string(str(literal))
    else:
        thelit=str(literal)
        if len(thelit)>100:
            thelit=thelit[0:100]
        raise ValueError(
            "The literal "+thelit+" ("+str(literal.datatype)+") is no known geometry literal type!"
        )


class AggBoundingBox(Accumulator):
    def __init__(self, aggregation: CompValue):
        super(AggBoundingBox, self).__init__(aggregation)
        self.value = shapely.empty(2)
        self.datatype = "http://www.opengis.net/ont/geosparql#wktLiteral"

    def update(self, row: FrozenBindings, aggregator: Aggregator) -> None:
        try:
            value = _eval(self.expr, row)
            dt = self.datatype
            if dt is None:
                dt = value.datatype
            else:
                # type error: Argument 1 to "type_promotion" has incompatible type "str"; expected "URIRef"
                dt = type_promotion(dt, value.datatype)  # type: ignore[arg-type]
            self.datatype = dt
            thegeom=processLiteralTypeToGeom(value)
            self.value = shapely.union(self.value,thegeom.envelope)
            if self.distinct:
                self.seen.add(value)
        except NotBoundError:
            # skip UNDEF
            pass

    def get_value(self) -> Literal:
        return Literal(self.value.to_wkt, datatype=self.datatype)

class AggBoundingCircle(Accumulator):
    def __init__(self, aggregation: CompValue):
        super(AggBoundingCircle, self).__init__(aggregation)
        self.value = shapely.empty(2)
        self.datatype = "http://www.opengis.net/ont/geosparql#wktLiteral"

    def update(self, row: FrozenBindings, aggregator: Aggregator) -> None:
        try:
            value = _eval(self.expr, row)
            dt = self.datatype
            if dt is None:
                dt = value.datatype
            else:
                # type error: Argument 1 to "type_promotion" has incompatible type "str"; expected "URIRef"
                dt = type_promotion(dt, value.datatype)  # type: ignore[arg-type]
            self.datatype = dt
            thegeom=processLiteralTypeToGeom(value)
            self.value = shapely.union(self.value,shapely.minimum_bounding_circle(thegeom))
            if self.distinct:
                self.seen.add(value)
        except NotBoundError:
            # skip UNDEF
            pass

    def get_value(self) -> Literal:
        return Literal(self.value.to_wkt, datatype=self.datatype)

class AggCentroid(Accumulator):
    def __init__(self, aggregation: CompValue):
        super(AggCentroid, self).__init__(aggregation)
        self.value = shapely.empty(2)
        self.datatype = "http://www.opengis.net/ont/geosparql#wktLiteral"

    def update(self, row: FrozenBindings, aggregator: Aggregator) -> None:
        try:
            value = _eval(self.expr, row)
            dt = self.datatype
            if dt is None:
                dt = value.datatype
            else:
                # type error: Argument 1 to "type_promotion" has incompatible type "str"; expected "URIRef"
                dt = type_promotion(dt, value.datatype)  # type: ignore[arg-type]
            self.datatype = dt
            thegeom=processLiteralTypeToGeom(value)
            self.value = shapely.union(self.value,thegeom)
            if self.distinct:
                self.seen.add(value)
        except NotBoundError:
            # skip UNDEF
            pass

    def get_value(self) -> Literal:
        return Literal(self.value.centroid.to_wkt, datatype=self.datatype)

class AggCollect(Accumulator):
    def __init__(self, aggregation: CompValue):
        super(AggCollect, self).__init__(aggregation)
        self.value = []
        self.datatype = "http://www.opengis.net/ont/geosparql#wktLiteral"

    def update(self, row: FrozenBindings, aggregator: Aggregator) -> None:
        try:
            value = _eval(self.expr, row)
            dt = self.datatype
            if dt is None:
                dt = value.datatype
            else:
                # type error: Argument 1 to "type_promotion" has incompatible type "str"; expected "URIRef"
                dt = type_promotion(dt, value.datatype)  # type: ignore[arg-type]
            self.datatype = dt
            thegeom=processLiteralTypeToGeom(value)
            self.value.append(thegeom)
            if self.distinct:
                self.seen.add(value)
        except NotBoundError:
            # skip UNDEF
            pass

    def get_value(self) -> Literal:
        return Literal(shapely.to_wkt(shapely.GeometryCollection(self.value)), datatype=self.datatype)

class AggConcaveHull(Accumulator):
    def __init__(self, aggregation: CompValue):
        super(AggConcaveHull, self).__init__(aggregation)
        self.value = shapely.empty(2)
        self.datatype = "http://www.opengis.net/ont/geosparql#wktLiteral"

    def update(self, row: FrozenBindings, aggregator: Aggregator) -> None:
        try:
            value = _eval(self.expr, row)
            dt = self.datatype
            if dt is None:
                dt = value.datatype
            else:
                # type error: Argument 1 to "type_promotion" has incompatible type "str"; expected "URIRef"
                dt = type_promotion(dt, value.datatype)  # type: ignore[arg-type]
            self.datatype = dt
            thegeom=processLiteralTypeToGeom(value)
            self.value = shapely.union(self.value,thegeom)
            if self.distinct:
                self.seen.add(value)
        except NotBoundError:
            # skip UNDEF
            pass

    def get_value(self) -> Literal:
        return Literal(shapely.concave_hull(self.value).to_wkt, datatype=self.datatype)

class AggConvexHull(Accumulator):
    def __init__(self, aggregation: CompValue):
        super(AggConvexHull, self).__init__(aggregation)
        self.value = shapely.empty(2)
        self.datatype = "http://www.opengis.net/ont/geosparql#wktLiteral"

    def update(self, row: FrozenBindings, aggregator: Aggregator) -> None:
        try:
            value = _eval(self.expr, row)
            dt = self.datatype
            if dt is None:
                dt = value.datatype
            else:
                # type error: Argument 1 to "type_promotion" has incompatible type "str"; expected "URIRef"
                dt = type_promotion(dt, value.datatype)  # type: ignore[arg-type]
            self.datatype = dt
            thegeom=processLiteralTypeToGeom(value)
            self.value = shapely.union(self.value,thegeom)
            if self.distinct:
                self.seen.add(value)
        except NotBoundError:
            # skip UNDEF
            pass

    def get_value(self) -> Literal:
        return Literal(shapely.convex_hull(self.value).to_wkt, datatype=self.datatype)


class AggUnion(Accumulator):
    def __init__(self, aggregation: CompValue):
        super(AggUnion, self).__init__(aggregation)
        self.value = shapely.empty(2)
        self.datatype = "http://www.opengis.net/ont/geosparql#wktLiteral"

    def update(self, row: FrozenBindings, aggregator: Aggregator) -> None:
        try:
            value = _eval(self.expr, row)
            dt = self.datatype
            if dt is None:
                dt = value.datatype
            else:
                # type error: Argument 1 to "type_promotion" has incompatible type "str"; expected "URIRef"
                dt = type_promotion(dt, value.datatype)  # type: ignore[arg-type]
            self.datatype = dt
            thegeom=processLiteralTypeToGeom(value)
            self.value = shapely.union(self.value,thegeom)
            if self.distinct:
                self.seen.add(value)
        except NotBoundError:
            # skip UNDEF
            pass

    def get_value(self) -> Literal:
        return Literal(self.value.to_wkt, datatype=self.datatype)