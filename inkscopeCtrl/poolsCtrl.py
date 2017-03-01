# Alpha O. Sall
# 03/24/2014

from flask import request, Response
import json
import requests
from array import *
import subprocess
from StringIO import StringIO
from InkscopeError import InkscopeError

class Pools:
    """docstring for pools"""
    def __init__(self):
        pass

    def newpool_attribute(self, jsonform):
        jsondata = json.loads(jsonform)
        self.name = jsondata['pool_name']
        self.pg_num = jsondata['pg_num']
        self.pgp_num = jsondata['pg_placement_num']
        self.type = jsondata['type']
        self.size = jsondata['size']
        self.min_size = jsondata['min_size']
        self.crash_replay_interval = jsondata['crash_replay_interval']
        self.crush_ruleset = jsondata['crush_ruleset']
        self.erasure_code_profile = jsondata['erasure_code_profile']
        self.quota_max_objects = jsondata['quota_max_objects']
        self.quota_max_bytes = jsondata['quota_max_bytes']

    def savedpool_attribute(self, ind, jsonfile):
        r = jsonfile.json()
        self.name = r['output']['pools'][ind]['pool_name']
        self.pg_num = r['output']['pools'][ind]['pg_num']
        self.pgp_num = r['output']['pools'][ind]['pg_placement_num']
        self.type = r['output']['pools'][ind]['type']
        self.size = r['output']['pools'][ind]['size']
        self.min_size = r['output']['pools'][ind]['min_size']
        self.crash_replay_interval = r['output']['pools'][ind]['crash_replay_interval']
        self.crush_ruleset = r['output']['pools'][ind]['crush_ruleset']
        self.erasure_code_profile = r['output']['pools'][ind]['erasure_code_profile']
        self.quota_max_objects = r['output']['pools'][ind]['quota_max_objects']
        self.quota_max_bytes = r['output']['pools'][ind]['quota_max_bytes']

    def register(self):
        uri = self.cephRestApiUrl+'osd/pool/create?pool='+self.name+'&pool_type='+self.type+'&pg_num='+str(self.pg_num)+'&pgp_num='+str(self.pgp_num)
        if self.erasure_code_profile != "":
            uri += '&erasure_code_profile='+self.erasure_code_profile
        register_pool = requests.put(uri)
        # if newpool.register().status_code != 200:
        # #     return 'Error '+str(r.status_code)+' on creating pools'
        # else:

class PoolsCtrl:
    def __init__(self,conf):
        self.cluster_name = conf['cluster']
        ceph_rest_api_subfolder = conf.get("ceph_rest_api_subfolder", "")
        ceph_rest_api_subfolder = ceph_rest_api_subfolder.strip('/')
        if ceph_rest_api_subfolder != '':
            ceph_rest_api_subfolder = "/" + ceph_rest_api_subfolder
        self.cephRestApiUrl = "http://"+conf.get("ceph_rest_api", "")+ceph_rest_api_subfolder+"/"
        pass

    def getCephRestApiUrl(self):
        return self.cephRestApiUrl

    def getindice(self,id, jsondata):
        r = jsondata.content
        r = json.loads(r)
        mypoolsnum = array('i',[])
        for i in r['output']['pools']:
            mypoolsnum.append(i[u'pool'])
        if id not in  mypoolsnum:
            return "Pool not found"
    
        else:
            for i in range(len(mypoolsnum)):
                if mypoolsnum[i]==id:
                    id=i
            return id
    
    
    def getpoolname(self,ind, jsondata):
    
        r = jsondata.json()
        poolname = r['output']['pools'][ind]['pool_name']
    
        return str(poolname)
    
    
    def checkpool(self,pool_id, jsondata):
        skeleton = {'status':'','output':{}}
        if isinstance(pool_id, int):
            ind = self.getindice(pool_id, jsondata)
            id = ind
            if id == "Pool id not found":
                skeleton['status'] = id
                result = json.dumps(skeleton)
                return Response(result, mimetype='application/json')
            else:
                skeleton['status'] = 'OK'
                result = json.dumps(skeleton)
                return Response(result, mimetype='application/json')
        if isinstance(pool_id, str):
            r = jsondata.content
            r = json.loads(r)
            mypoolsname = array('i',[])
            for i in r['output']:
                mypoolsname.append(i[u'poolname'])
            if pool_id not in  mypoolsname:
                skeleton['status'] = 'OK'
                result = json.dumps(skeleton)
                return Response(result, mimetype='application/json')
            else:
                skeleton['status'] = pool_id+'already exits. Please enter a new pool name'
                result = json.dumps(skeleton)
                return Response(result, mimetype='application/json')
    

    def pool_list(self):
        args = ['ceph',
                'osd',
                'lspools',
                '--format=json',
                '--cluster='+ self.cluster_name ]
        output = subprocess.Popen(args, stdout=subprocess.PIPE).communicate()[0]
        output_io = StringIO(output)
        return output_io
    
    
    # @app.route('/pools/', methods=['GET','POST'])
    # @app.route('/pools/<int:id>', methods=['GET','DELETE','PUT'])
    def pool_manage(self,id):
        cephRestApiUrl = self.getCephRestApiUrl();
        if request.method == 'GET':
            if id == None:
    
                r = requests.get(cephRestApiUrl+'osd/lspools.json')
    
                if r.status_code != 200:
                    return Response(r.raise_for_status())
                else:
                    r = r.content
                    return Response(r, mimetype='application/json')
    
            else:
                data = requests.get(cephRestApiUrl+'osd/dump.json')
                if data.status_code != 200:
                    raise InkscopeError( data.status_code, 'Error '+str(data.status_code)+' on the request getting pools: '+data.content)
                else:
    
                    ind = self.getindice(id, data)
                    id = ind
                    skeleton = {'status':'','output':{}}
                    if id == "Pool id not found":
                        skeleton['status'] = id
                        result = json.dumps(skeleton)
                        return Response(result, mimetype='application/json')
    
                    else:
    
                        r = data.content
                        r = json.loads(r)
                        #r = data.json()
                        skeleton['status'] = r['status']
                        skeleton['output'] = r['output']['pools'][id]
    
                        result = json.dumps(skeleton)
                        return Response(result, mimetype='application/json')
    
        elif request.method =='POST':
            jsonform = request.form['json']
            newpool = Pools()
            newpool.cephRestApiUrl = cephRestApiUrl
            newpool.newpool_attribute(jsonform)
    
            newpool.register()
    
            jsondata = requests.get(cephRestApiUrl+'osd/dump.json')
    
            r = jsondata.content
            r = json.loads(r)
            #r = jsondata.json()
            nbpool = len(r['output']['pools'])
    
            poolcreated = Pools()
            poolcreated.savedpool_attribute(nbpool-1, jsondata)
    
            # set pool parameter
    
            var_name= ['size', 'min_size', 'crash_replay_interval','crush_ruleset']
            param_to_set_list = [newpool.size, newpool.min_size, newpool.crash_replay_interval, newpool.crush_ruleset]
            default_param_list = [poolcreated.size, poolcreated.min_size, poolcreated.crash_replay_interval, poolcreated.crush_ruleset]
    
            for i in range(len(default_param_list)):
                if param_to_set_list[i] != default_param_list[i]:
                    r = requests.put(cephRestApiUrl+'osd/pool/set?pool='+str(poolcreated.name)+'&var='+var_name[i]+'&val='+str(param_to_set_list[i]))
                else:
                    pass
    
            # set object or byte limit on pool
    
            field_name = ['max_objects','max_bytes']
            param_to_set = [newpool.quota_max_objects, newpool.quota_max_bytes]
            default_param = [poolcreated.quota_max_objects, poolcreated.quota_max_bytes]
    
            for i in range(len(default_param)):
                if param_to_set[i] != default_param[i]:
                    r = requests.put(cephRestApiUrl+'osd/pool/set-quota?pool='+str(poolcreated.name)+'&field='+field_name[i]+'&val='+str(param_to_set[i]))
    
                else:
                    pass
            return 'None'
    
        elif request.method == 'DELETE':
            data = requests.get(cephRestApiUrl+'osd/dump.json')
            # if data.status_code != 200:
            #     return 'Error '+str(r.status_code)+' on the request getting pools'
            # else:
            #r = data.json()
            r = data.content
            r = json.loads(r)
    
            # data = requests.get('http://localhost:8080/ceph-rest-api/osd/dump.json')
            ind = self.getindice(id, data)
            id = ind
    
            poolname = r['output']['pools'][id]['pool_name']
            poolname = str(poolname)
            delete_request = requests.put(cephRestApiUrl+'osd/pool/delete?pool='+poolname+'&pool2='+poolname+'&sure=--yes-i-really-really-mean-it')
            print "Delete code ", delete_request.status_code
            print "Delete message ",delete_request.content
            if delete_request.status_code != 200:
                raise InkscopeError(delete_request.status_code, delete_request.content)
            return "pool has been deleted"
    
        else:
    
            jsonform = request.form['json']
            newpool = Pools()
            newpool.newpool_attribute(jsonform)
    
            data = requests.get(cephRestApiUrl+'osd/dump.json')
            if data.status_code != 200:
                raise InkscopeError( data.status_code, 'Error '+str(data.status_code)+' on the request getting pools: '+data.content)
            else:
                #r = data.json()
                r = data.content
                r = json.loads(r)
                ind = self.getindice(id, data)
                savedpool = Pools()
                savedpool.savedpool_attribute(ind, data)
    
                # rename the poolname
    
                if str(newpool.name) != str(savedpool.name):
                    r = requests.put(cephRestApiUrl+'osd/pool/rename?srcpool='+str(savedpool.name)+'&destpool='+str(newpool.name))
    
                # set pool parameter
    
                var_name= ['size', 'min_size', 'crash_replay_interval','pg_num','pgp_num','crush_ruleset']
                param_to_set_list = [newpool.size, newpool.min_size, newpool.crash_replay_interval, newpool.pg_num, newpool.pgp_num, newpool.crush_ruleset]
                default_param_list = [savedpool.size, savedpool.min_size, savedpool.crash_replay_interval, savedpool.pg_num, savedpool.pgp_num, savedpool.crush_ruleset]

                message = ""
                for i in range(len(default_param_list)):
                    if param_to_set_list[i] != default_param_list[i]:
                        print "set ", var_name[i], " to ", str(param_to_set_list[i])
                        r = requests.put(cephRestApiUrl+'osd/pool/set?pool='+str(newpool.name)+'&var='+var_name[i]+'&val='+str(param_to_set_list[i]))
                        if r.status_code != 200:
                            message= message+ "Can't set "+ var_name[i]+ " to "+ str(param_to_set_list[i])+ " : "+ r.content+"<br>"
                    else:
                        pass
    
                # set object or byte limit on pool
    
                field_name = ['max_objects','max_bytes']
                param_to_set = [newpool.quota_max_objects, newpool.quota_max_bytes]
                default_param = [savedpool.quota_max_objects, savedpool.quota_max_bytes]
    
                for i in range(len(default_param)):
                    if param_to_set[i] != default_param[i]:
                        r = requests.put(cephRestApiUrl+'osd/pool/set-quota?pool='+str(newpool.name)+'&field='+field_name[i]+'&val='+str(param_to_set[i]))
                        if r.status_code != 200:
                            message= message+ "Can't set "+ field_name[i]+ " to "+ str(param_to_set[i])+ " : "+ r.content+"<br>"
                    else:
                        pass

                return message
    
    
    # @app.route('/pools/<int:id>/snapshot', methods=['POST'])
    def makesnapshot(self,id):
        cephRestApiUrl = self.getCephRestApiUrl();
        data = requests.get(cephRestApiUrl+'osd/dump.json')
        #r = data.json()
        r = data.content
        r = json.loads(r)
        ind = self.getindice(id,data)
        id = ind
    
        poolname = r['output']['pools'][id]['pool_name']
    
        jsondata = request.form['json']
        jsondata = json.loads(jsondata)
        snap = jsondata['snapshot_name']
        r = requests.put(cephRestApiUrl+'osd/pool/mksnap?pool='+str(poolname)+'&snap='+str(snap))
        if r.status_code != 200:
                raise InkscopeError(r.status_code, r.content)
        return r.content
    
    
    # @app.route('/pools/<int:id>/snapshot/<namesnapshot>', methods=['DELETE'])
    def removesnapshot(self,id, namesnapshot):
        cephRestApiUrl = self.getCephRestApiUrl();
        data = requests.get(cephRestApiUrl+'osd/dump.json')
        #r = data.json()
        r = data.content
        r = json.loads(r)
        ind = self.getindice(id,data)
        id = ind
    
        poolname = r['output']['pools'][id]['pool_name']
    
        r = requests.put(cephRestApiUrl+'osd/pool/rmsnap?pool='+str(poolname)+'&snap='+str(namesnapshot))
        if r.status_code != 200:
                raise InkscopeError(r.status_code, r.content)
        return r.content
