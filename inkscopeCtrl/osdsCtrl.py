# Alain Dechorgnat
# 05/19/2014

from flask import Flask, request, Response
import json
import requests
from array import *


# def getCephRestApiUrl(request):
#     # discover ceph-rest-api URL
#     return request.url_root.replace("inkscopeCtrl","ceph-rest-api")

class OsdsCtrl:
    """docstring for OsdsCtrl"""
    def __init__(self, conf):
        ceph_rest_api_subfolder = conf.get("ceph_rest_api_subfolder", "")
        ceph_rest_api_subfolder = ceph_rest_api_subfolder.strip('/')
        if ceph_rest_api_subfolder != '':
            ceph_rest_api_subfolder = "/" + ceph_rest_api_subfolder
        self.cephRestApiUrl = "http://"+conf.get("ceph_rest_api", "")+ceph_rest_api_subfolder+"/"
        pass

    def osds_manage(self, id):
        # cephRestApiUrl = getCephRestApiUrl(request);
        action = request.form.get("action","none");
        if action == "reweight-by-utilisation" :
            print "reweight-by-utilisation"
            r = requests.put(self.cephRestApiUrl + 'osd/reweight-by-utilization')
            print str(r.content)
            return str(r.content)
        else :
            print "unknown command"
