class TestUtils:

    @staticmethod
    def getQueryListForTwoLiterals(query,combinations,config, scombinations=[("WKT","WKT")], onlyWKT=False):
        result = []
        if onlyWKT:
            for comb in scombinations:
                result.append((TestUtils.rewriteQueryForLiteralType(comb[0], comb[1], query,config), str(comb[0]) + "-" + str(comb[1])))
        else:
            for comb in combinations:
                result.append((TestUtils.rewriteQueryForLiteralType(comb[0], comb[1], query,config), str(comb[0]) + "-" + str(comb[1])))
        return result

    @staticmethod
    def rewriteQueryForLiteralType(literaltype1, literaltype2, thequery,config):
        thequery = thequery.replace("%%literalrel1%%", config["geoProperties"][literaltype1]).replace("%%literalrel2%%",
                                                                                                      config[
                                                                                                          "geoProperties"][
                                                                                                          literaltype2])
        return thequery.replace("%%literal1%%", config["literalTypes"][literaltype1]).replace("%%literal2%%",
                                                                                              config["literalTypes"][
                                                                                                  literaltype2])
    @staticmethod
    def queryExecution(query,combinations,config, g):
        querylist = TestUtils.getQueryListForTwoLiterals(query,combinations,config,[("WKT","WKT")], False)
        resultlist = []
        for q in querylist:
            result = g.query(q[0])
            if result is not None and len(result.bindings)>0:
                resultlist.append(([{str(k): v for k, v in i.items()} for i in result.bindings], q[1]))
            else:
                resultlist.append(([],q[1]))
        return resultlist