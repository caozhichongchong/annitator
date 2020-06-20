#!/usr/bin/python

import argparse, json, os, sys, urllib.request
from html.parser import HTMLParser

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
        maxCacheSize = 1000
        if len(self.responses) > maxCacheSize:
            self.responses = self.responses[-maxCacheSize:]
        for response in self.responses:
            jsonDict = {"url": response.url, "contents": response.contents}
            jsonList.append(jsonDict)
        cacheDir = os.path.dirname(self.cachePath)
        if not os.path.isdir(cacheDir):
            os.mkdirs(cacheDir)
        open(self.cachePath, 'w').write(json.dumps(jsonList))
        
    def getUrl(self, url):
        for response in self.responses:
            if response.url == url:
                print("Getting url '" + url + "', reusing cached response")
                return response.contents
        return self._downloadUrl(url)

    def _downloadUrl(self, url):
        # download url
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

def main():
    parser = argparse.ArgumentParser(
        description = """
            Annotates genes using the annitator algorithm
            Takes as input a csv file of genes.
            Generates a new csv file containing annotation information in a new column
            """
    )
    parser.add_argument("--input", nargs=1)
    parser.add_argument("--output", nargs=1)
    args = parser.parse_args()

    downloader = UrlDownloader("urlcache")
    url = searchUniProt("rpoE", downloader)
    print("uniprot result = " + str(url))

if __name__ == "__main__":
    main()
