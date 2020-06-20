#!/usr/bin/python

import argparse, json, os, sys, urllib.request

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

def main():
    parser = argparse.ArgumentParser(
        description = """
            Annotates genes using the FastANNI algorithm
            Takes as input a csv file of genes.
            Generates a new csv file containing annotation information in a new column
            """
    )
    parser.add_argument("--input", nargs=1)
    parser.add_argument("--output", nargs=1)
    args = parser.parse_args()

    downloader = UrlDownloader("urlcache")
    response = downloader.getUrl("https://uniprot.org/uniprot/?query=PMT1")
    print("url response = '" + str(response))


if __name__ == "__main__":
    main()
