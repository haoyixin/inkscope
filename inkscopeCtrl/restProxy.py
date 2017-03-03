from flask import Flask, request, Response
import json
import requests

class RestProxy:
    """docstring for RestProxy"""
    def __init__(self, conf):
        ceph_rest_api_subfolder = conf.get("ceph_rest_api_subfolder", "")
        ceph_rest_api_subfolder = ceph_rest_api_subfolder.strip('/')
        if ceph_rest_api_subfolder != '':
            ceph_rest_api_subfolder = "/" + ceph_rest_api_subfolder
        self.cephRestApiUrl = "http://" + \
            conf.get("ceph_rest_api", "") + ceph_rest_api_subfolder + "/"
        pass

    def proxy_get(self, url):
        p = request.args
        r = requests.get(self.cephRestApiUrl + url, params=p)
        if r.status_code != 200:
            return Response(r.raise_for_status())
        else:
            return Response(r.content, mimetype='application/json')

    def proxy_put(self, url):
        p = request.args
        r = requests.put(self.cephRestApiUrl + url, params=p)
        if r.status_code != 200:
            return Response(r.raise_for_status())
        else:
            return Response(r.content, mimetype='application/json')
