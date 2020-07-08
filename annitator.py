#!/usr/bin/python

import argparse, collections, json, os, sys, urllib.request,urllib.parse, time
from html.parser import HTMLParser
import xml.etree.ElementTree as ET

class UrlResponse():
    def __init__(self, url, contents):
        self.url = url
        self.contents = contents

class UrlDownloader():
    def __init__(self, cacheDir):
        self.cachePath = os.path.abspath(os.path.join(cacheDir, "cache.json"))
        self.responses = []
        self.loadCache()

    def loadCache(self):
        if os.path.isfile(self.cachePath):
            cacheContents = open(self.cachePath).read()
            jsonList = json.loads(cacheContents)
            responses = []
            for item in jsonList:
                response = UrlResponse(item["url"], item["contents"])
                responses.append(response)
            self.responses = responses

    def saveCache(self):
        jsonList = []
        maxCacheSize = 5000
        if len(self.responses) > maxCacheSize:
            self.responses = self.responses[-maxCacheSize:]
        for response in self.responses:
            jsonDict = {"url": response.url, "contents": response.contents}
            jsonList.append(jsonDict)
        cacheDir = os.path.dirname(self.cachePath)
        if not os.path.isdir(cacheDir):
            os.makedirs(cacheDir)
        open(self.cachePath, 'w').write(json.dumps(jsonList))
        
    def getUrl(self, url):
        for response in self.responses:
            if response.url == url:
                print("Getting url '" + url + "', reusing cached response")
                return response.contents
        return self._downloadUrl(url)

    def _downloadUrl(self, url):
        # download url
        time.sleep(2)
        print("Downloading url '" + url + "', not using cache")
        response = urllib.request.urlopen(url)
        data = response.read()
        text = data.decode('utf-8')
        # save into cache
        self.responses.append(UrlResponse(url, text))
        self.saveCache()
        return text

class HtmlFormatter(HTMLParser):
    def __init__(self):
        super(HtmlFormatter, self).__init__()
        self.texts = []
        self.indent = 0

    def format(self):
        return "\n".join(self.texts)

    def addText(self, text):
        indent = " " * self.indent
        self.texts.append(indent + text.replace("\n", indent))

    def handle_starttag(self, tag, attrs):
        texts = [str(x) for x in [tag] + attrs]
        self.addText("<" + ",".join(texts) + ">")
        self.indent += 1

    def handle_data(self, data):
        self.addText(data)

    def handle_endtag(self, tag):
        self.indent -= 1
        self.addText("</" + tag + ">")

def prettyFormatHtml(text):
    formatter = HtmlFormatter()
    formatter.feed(text)
    return formatter.format()

# a search result from uniprot
class UniProtSearchResult():
    def __init__(self, url, species):
        self.url = url
        self.species = species

    def __repr__(self):
        return "(url:" + str(self.url) + ",species:" + str(self.species) + ")"

# parses the search results page of uniprot
# TODO: instead download from https://www.uniprot.org/uniprot/?query=rpoE&sort=score&format=tab&limit=10
class UniProtSearchResultsParser(HTMLParser):
    def __init__(self):
        super(UniProtSearchResultsParser, self).__init__()
        self.results = []
        self.columnLabels = {}
        self.parsingTableHeader = False
        self.parsingTableBody = False
        self.tableColumnIndex = 0
        self.currentUrl = None
        self.currentSpecies = None

    def handle_starttag(self, tag, attrs):
        if not self.parsingTableHeader and tag == "thead":
            self.parsingTableHeader = True
            self.tableColumnIndex = 0
        if not self.parsingTableBody and tag == "tbody":
            self.parsingTableBody = True
            self.tableColumnIndex = 0

        if self.parsingTableBody:
            if tag == "tr":
                self.tableColumnIndex = 0
            if self.columnLabels[self.tableColumnIndex] == "Entry":
                if tag == "a":
                    url = None
                    for attr in attrs:
                        if attr[0] == "href":
                            url = attr[1]
                    if url is not None:
                        self.currentUrl = url

    def handle_data(self, data):
        if self.parsingTableHeader:
            self.columnLabels[self.tableColumnIndex] = data
        if self.parsingTableBody and self.columnLabels[self.tableColumnIndex] == "Organism":
            self.currentSpecies = data

    def handle_endtag(self, tag):
        if tag == "thead":
            self.parsingTableHeader = False
        if tag == "tbody":
            self.parsingTableBody = False

        if tag == "th":
            if self.parsingTableHeader:
                if self.tableColumnIndex not in self.columnLabels:
                    self.columnLabels[self.tableColumnIndex] = ""
                self.tableColumnIndex += 1
        if tag == "td":
            if self.parsingTableBody:
                self.tableColumnIndex += 1

        if self.currentUrl is not None and self.currentSpecies is not None:
            self.results.append(UniProtSearchResult(self.currentUrl, self.currentSpecies))
            self.currentUrl = None
            self.currentSpecies = None


def searchUniProt(query, urlDownloader):
    rootUrl = "https://uniprot.org"
    query = urllib.parse.quote(query)
    searchResults = urlDownloader.getUrl(rootUrl + "/uniprot/?query=" + query + "&sort=score")
    parser = UniProtSearchResultsParser()
    parser.feed(searchResults)
    results = parser.results
    interestingResults = []
    for result in results:
        interesting = True
        speciesLower = result.species.lower()
        if "human" in speciesLower or "mouse" in speciesLower or "yeast" in speciesLower:
            interesting = False
        if interesting:
            interestingResults.append(result)
    if len(interestingResults) > 0:
        return rootUrl + interestingResults[0].url
    return None

def getUniProtEntryContents(url, urlDownloader):
    urlContents = urlDownloader.getUrl(url + ".xml")
    return urlContents

class UniProtEntry():
    def __init__(self):
        self.entry = None
        self.protein = None
        self.gene = None
        self.organism = None
        self.status = None
        self.function = None
        self.functionPublications = None
        self.pathway = None
        self.biologicalProcesses = None
        self.disruptionPhenotype = None

    def __str__(self):
        components = collections.OrderedDict()
        components["entry"] = self.entry
        components["protein"] = self.protein
        components["gene"] = self.gene
        components["organism"] = self.organism
        components["status"] = self.status
        components["function"] = self.function
        components["functionPublications"] = self.functionPublications
        components["pathway"] = self.pathway
        components["biologicalProcesses"] = self.biologicalProcesses
        components["distruptionPhenotype"] = self.disruptionPhenotype
        lines = []
        for key, value in components.items():
            if value is None:
                value = "unknown"
            lines.append(key + ": " + str(value))
        return ",\n".join(lines)
    

# converts from a list of components into the xpath format
# the xpath format is required for querying an ElementTree
def makeXpathQuery(namespace, path):
    return "/".join(["."] + [namespace + pathComponent for pathComponent in path])

def findXmlNodes(root, namespace, path):
    query = makeXpathQuery(namespace, path)
    result = root.findall(query)
    return result

def findXmlNode(root, namespace, path):
    query = makeXpathQuery(namespace, path)
    nodes = root.findall(query)
    if len(nodes) == 1:
        return nodes[0]
    #print("Found nodes " + str(nodes) + " for query " + query)
    return None
    
def parseUniProtEntry(text, entry):
    tree = ET.fromstring(text)
    parsed = UniProtEntry()
    parsed.entry = entry
    namespace = "{http://uniprot.org/uniprot}"

    xmlNameNode = findXmlNode(tree, namespace, ["entry", "protein", "recommendedName", "fullName"])
    if xmlNameNode is not None:
        parsed.protein = xmlNameNode.text

    geneNode = findXmlNode(tree, namespace, ["entry", "gene", "name[@type='primary']"])
    if geneNode is not None:
        parsed.gene = geneNode.text

    organismNode = findXmlNode(tree, namespace, ["entry", "organism", "name[@type='scientific']"])
    if organismNode is not None:
        parsed.organism = organismNode.text

    parsed.status = "ANNITATOR DOES NOT YET KNOW HOW TO PARSE 'status', SORRY"

    functionNode = findXmlNodes(tree, namespace, ["entry", "comment[@type='function']", "text"])
    functionSet = []
    if functionNode is not None:
        for node in functionNode:
            functionSet.append(node.text)

    functionNode = findXmlNodes(tree, namespace, ["entry", "comment[@type='activity regulation']", "text"])
    if functionNode is not None:
        for node in functionNode:
            functionSet.append(node.text)

    parsed.function = '; '.join(functionSet)

    functionPublicationsNode = findXmlNodes(tree, namespace, ["entry", "reference[@key]", "citation", "title"])
    if functionPublicationsNode is not None:
        functionPublications = []
        for node in functionPublicationsNode:
            functionPublications.append(node.text)
        parsed.functionPublications = '; '.join(functionPublications)
    #parsed.functionPublications = "ANNITATOR DOES NOT YET KNOW HOW TO PARSE function publications, SORRY"

    pathwayNode = findXmlNode(tree, namespace, ["entry", "comment[@type='pathway']", "text"])
    if pathwayNode is not None:
        parsed.pathway = pathwayNode.text

    processNodes = findXmlNodes(tree, namespace, ["entry", "dbReference[@type='GO']", "property[@type='term']"])
    if len(processNodes) > 0:
        processes = []
        for node in processNodes:
            if "value" in node.attrib:
                value = node.attrib["value"]
                prefix = "P:"
                if value.startswith(prefix):
                    processes.append(value[len(prefix):])
        parsed.biologicalProcesses = processes

    disruptionNode = findXmlNode(tree, namespace, ["entry", "comment[@type='disruption phenotype']", "text"])
    if disruptionNode is not None:
        parsed.disruptionPhenotype = disruptionNode.text
    
    return parsed

def parsedEntriesToCsv(parsed):
    tempList = [
        str(parsed.entry),
        str(parsed.protein),
        str(parsed.gene),
        str(parsed.organism),
        str(parsed.function),
        str(parsed.pathway),
        '; '.join(parsed.biologicalProcesses),
        str(parsed.disruptionPhenotype),
        str(parsed.functionPublications)]
    tempLine = '\t'.join([tempFactor.replace('\t',' ') for tempFactor in tempList])
    return tempLine + '\n'


def main():
    parser = argparse.ArgumentParser(
        description = """
            Annotates genes using the annitator algorithm
            Takes as input a csv file of genes.
            Generates a new csv file containing annotation information in a new column
            """
    )
    parser.add_argument('-i',
                        default="example.txt",
                        action='store', type=str,
                        metavar='input_function_list.txt',
                        help="input list of your functions separated by new line\n")
    parser.add_argument('-o',
                        default="annotation.csv", action='store', type=str, metavar='annotation.csv',
                        help="output csv filename to store the annotations")
    args = parser.parse_args()

    print("Loading " + str(args.i))
    queries = []
    with open(args.i) as inputFile:
        lines = inputFile.readlines()
        queries = [line.strip() for line in lines]
    print("Read queries of " + str(queries))

    print("Downloading data")
    downloader = UrlDownloader("urlcache")
    parsedEntries = []
    for query in queries:
        for sub_query in query.split(';'):
            url = searchUniProt(sub_query, downloader)
            print("uniprot query result: " + str(url))
            if url is not None:
                text = getUniProtEntryContents(url, downloader)
                parsed = parseUniProtEntry(text, query)
                parsedEntries.append(parsed)

    print("Saving results to " + str(args.o))
    outputLines = []
    outputLinesCsv = []
    headLines = 'entry\tprotein\tgene\torganism\tfunction\tpathway\tGO_biology\tdisruptionPhenotype\tPublication\n'
    for parsed in parsedEntries:
        line = str(parsed)
        outputLines.append(line)
        outputLinesCsv.append(parsedEntriesToCsv(parsed))
    with open(args.o, 'w') as outputFile:
        outputFile.write("\n\n".join(outputLines))
    with open(args.o + '.csv', 'w') as outputFile:
        outputFile.write(headLines + "".join(outputLinesCsv))
    print("Done")

if __name__ == "__main__":
    main()
