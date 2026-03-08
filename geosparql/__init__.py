from .geosparql import *
from rdflib import Namespace

__version__ = "0.2"
GEOF = Namespace("http://www.opengis.net/def/function/geosparql/")
GEOFEXT = Namespace("http://www.opengis.net/def/function/geosparql/ext/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")

getfuncs()
