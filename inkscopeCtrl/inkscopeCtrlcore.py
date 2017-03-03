# Alpha O. Sall
# Alain Dechorgnat
# 03/24/2014

# 2015-12 A. Dechorgnat: add login security (inspired from http://thecircuitnerd.com/flask-login-tokens/)


from flask import Flask, Response, redirect
from flask_login import (LoginManager, login_required, login_user,
                         current_user, logout_user, UserMixin)
from itsdangerous import URLSafeTimedSerializer
from datetime import timedelta
from hashlib import md5
from bson.json_util import dumps
from InkscopeError import InkscopeError

from werkzeug.routing import BaseConverter

class RegexConverter(BaseConverter):

    def __init__(self, url_map, *items):
        super(RegexConverter, self).__init__(url_map)
        self.regex = items[0]

version = "1.4.0"

app = Flask(__name__)
app.url_map.converters['regex'] = RegexConverter

app.secret_key = "Mon Nov 30 17:20:29 2015"
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=14)

#Login_serializer used to encryt and decrypt the cookie token for the remember
#me option of flask-login
login_serializer = URLSafeTimedSerializer(app.secret_key)

login_manager = LoginManager()
login_manager.init_app(app)

from subprocess import CalledProcessError

import mongoJuiceCore

from poolsCtrl import PoolsCtrl,Pools
from osdsCtrl import OsdsCtrl
from restProxy import RestProxy
from rbdCtrl import RbdCtrl
import subprocess
from StringIO import StringIO
#import probesCtrl

from S3Ctrl import S3Ctrl, S3Error
from S3ObjectCtrl import *

def hash_pass(password):
    """
    Return the md5 hash of the password+salt
    """
    salted_password = password + app.secret_key
    return md5(salted_password).hexdigest()



# Load configuration from file
configfile = "/opt/inkscope/etc/inkscope.conf"
datasource = open(configfile, "r")
conf = json.load(datasource)
datasource.close()

# control inkscope users  collection in mongo
db = mongoJuiceCore.getClient(conf, 'inkscope')
if db.inkscope_users.count() == 0:
    print "list users is empty: populating with default users"
    user = {"name":"admin",
            "password": hash_pass("admin"),
            "roles":["admin"]}
    db.inkscope_users.insert(user)
    user = {"name":"guest",
            "password": hash_pass(""),
            "roles":["supervizor"]}
    db.inkscope_users.insert(user)


#
# Security
#
class User(UserMixin):

    def __init__(self, name, password, roles):
        self.id = name
        self.password = password
        self.roles = roles

    @staticmethod
    def get(userid):
        """
        Static method to search the database and see if userid exists.  If it
        does exist then return a User Object.  If not then return None as
        required by Flask-Login.
        """
        u = db.inkscope_users.find_one({"name":userid})
        if u:
            return User(u['name'], u['password'], u['roles'])
        return None


    def get_auth_token(self):
        """
        Encode a secure token for cookie
        """
        data = [str(self.id), self.password]
        return login_serializer.dumps(data)


def get_ceph_version():
    try:
        args = ['ceph',
                '--version']
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = p.communicate()
        if p.returncode != 0:
            return "not found"
        ceph_version = re.search('[0-9]*\.[0-9]*\.[0-9]*', output)
        if ceph_version:
            return ceph_version.group(0)
        return "not found"
    except:
        return '0.0.0 (could not be found on inkscope server - Please consider to install Ceph on it)'

def get_ceph_version_name(ceph_version):
    major, minor, revision = ceph_version.split(".")
    if major == '12':
        return 'Luminous'
    if major == '11':
        return 'Kraken'
    if major == '10':
        return 'Jewel'
    if major == '9':
        return 'Infernalis'
    if major == '0':
        minor = int(minor)
        if minor == 94:
            return 'Hammer'
        if minor > 87:
            return 'Hammer (pre-version)'
        if minor == 87:
            return 'Giant'
        if minor > 80:
            return 'Giant (pre-version)'
        if minor == 80:
            return 'Firefly'
        if minor > 72:
            return 'Firefly (pre-version)'
        if minor == 72:
            return 'Emperor'
        if minor > 67:
            return 'Emperor (pre-version)'
        if minor == 67:
            return 'Dumpling'
        if minor == 0:
            return 'Unavailable'
        return 'Really too old'


@login_manager.user_loader
def load_user(userid):
    """
    Flask-Login user_loader callback.
    The user_loader function asks this function to get a User Object or return
    None based on the userid.
    The userid was stored in the session environment by Flask-Login.
    user_loader stores the returned User object in current_user during every
    flask request.
    """
    return User.get(userid)


@login_manager.token_loader
def load_token(token):
    """
    Flask-Login token_loader callback.
    The token_loader function asks this function to take the token that was
    stored on the users computer process it to check if its valid and then
    return a User Object if its valid or None if its not valid.
    """

    #The Token itself was generated by User.get_auth_token.  So it is up to
    #us to known the format of the token data itself.

    #The Token was encrypted using itsdangerous.URLSafeTimedSerializer which
    #allows us to have a max_age on the token itself.  When the cookie is stored
    #on the users computer it also has a exipry date, but could be changed by
    #the user, so this feature allows us to enforce the exipry date of the token
    #server side and not rely on the users cookie to exipre.
    max_age = app.config["REMEMBER_COOKIE_DURATION"].total_seconds()

    #Decrypt the Security Token, data = [username, hashpass]
    data = login_serializer.loads(token, max_age=max_age)

    #Find the User
    user = User.get(data[0])

    #Check Password and return user or None
    if user and data[1] == user.password:
        return user
    return None


@app.route("/login/", methods=["GET", "POST"])
def login_page():
    """
    Web Page to Display Login Form and process form.
    """
    if request.method == "POST":
        user = User.get(request.form['name'])
        # If we found a user based on username then compare that the submitted
        # password matches the password in the database.  The password is stored
        # is a slated hash format, so you must hash the password before comparing
        # it.
        if user and hash_pass(request.form['password']) == user.password:
            login_user(user, remember=True)
            return redirect(request.args.get("next") or "/inkscopeViz/index.html")
        else:
            return redirect('/inkscopeViz/login.html?result=failed')
    return redirect("/inkscopeViz/login.html", code=302)


@app.route('/logout')
def logout():
    logout_user()
    return redirect("/inkscopeViz/login.html", code=302)


#
# global management
#
@app.route('/conf.json', methods=['GET'])
@login_required  # called by every page, so force to be identified
def conf_manage():
    #force platform field to invite admin to give a name to this instance
    conf['platform'] = conf.get('platform')
    if conf['platform'] is None or conf['platform'] == "":
        conf['platform'] = "fill 'platform' field in inkscope.conf"
    ceph_version = get_ceph_version()
    if 'admin' in current_user.roles:
        conf['version'] = version
        conf['ceph_version'] = ceph_version
        conf['ceph_version_name'] = get_ceph_version_name(ceph_version)
        conf['roles'] = current_user.roles
        conf['username']= current_user.id
        return Response(json.dumps(conf), mimetype='application/json')
    else:
        conflite = {}
        conflite['version'] = version
        conflite['ceph_version'] = ceph_version
        conflite['ceph_version_name'] = get_ceph_version_name(ceph_version)
        conflite['roles'] = current_user.roles
        conflite['platform'] = conf.get('platform')
        conflite['cluster'] = conf.get('cluster')
        conflite['username']= current_user.id
        try:
            conflite['influxdb_endpoint'] = conf.get('influxdb_endpoint')
        except:
            pass
        return Response(json.dumps(conflite), mimetype='application/json')


#
# inkscope users management
#
@app.route('/inkscope_user', methods=['GET'])
@login_required
def inkscope_user_list():
    r = Response(dumps(db.inkscope_users.find()))
    print r
    return r


@app.route('/inkscope_user/<id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def inkscope_user_manage(id):
    if request.method == 'GET':
        # user info
        return  Response(dumps(db.inkscope_users.find_one({"name":id})))

    elif request.method == 'POST':
        # user creation
        if 'admin' not in current_user.roles:
            return Response("Not enough permissions to do this", status=403)
        if db.inkscope_users.find_one({"name":id}):
            return Response("This user already exists", status=403)
        user = json.loads(request.data)
        user['password']= hash_pass(user['password'])
        db.inkscope_users.insert(user)
        return Response('ok', status=201)

    elif request.method == 'PUT':
        # user modification
        if 'admin' not in current_user.roles:
            return Response("Not enough permissions to do this", status=403)
        print 'old', dumps(db.inkscope_users.find_one({"name":id}))
        user = json.loads(request.data)
        if 'newpassword' in user:
            user['password']= hash_pass(user['newpassword'])
            del user['newpassword']
        del user['_id']

        print 'rep', dumps(user)
        newuser = db.inkscope_users.update({"name":id}, user)
        print 'old', dumps(db.inkscope_users.find_one({"name":id}))
        return Response('ok')

    elif request.method == 'DELETE':
        # user deletion
        if 'admin' not in current_user.roles:
            return Response("Not enough permissions to do this", status=403)
        if current_user.id == id:
            return Response("You can't delete yourself", status=403)
        else:
            db.inkscope_users.remove({"name":id})
            return Response('ok')


@app.route('/inkscope_user_role/', methods=['GET'])
@login_required
def inkscope_user_role_list():
    roles = ["admin","admin_rgw","admin_rbd","admin_pool","supervizor"]
    return Response(dumps(roles), mimetype='application/json')


#
# mongoDB query facility
#
@app.route('/<db>/<collection>', methods=['GET', 'POST'])
@login_required
def find(db, collection):
    return mongoJuiceCore.find(conf, db, collection)


@app.route('/<db>', methods=['POST'])
@login_required
def full(db):
    return mongoJuiceCore.full(conf, db)


#
# Pools management
#
@app.route('/poolList/', methods=['GET'])
@login_required
def pool_list():
    try:
        return Response(PoolsCtrl(conf).pool_list(), mimetype='application/json')
    except InkscopeError as e:
        return Response(e.message, e.status)


@app.route('/pools/', methods=['GET', 'POST'])
@app.route('/pools/<int:id>', methods=['GET', 'DELETE', 'PUT'])
@login_required
def pool_manage(id=None):
    try:
        return PoolsCtrl(conf).pool_manage(id)
    except InkscopeError as e:
        return Response(e.message, e.status)


@app.route('/pools/<int:id>/snapshot', methods=['POST'])
@login_required
def makesnapshot(id):
    try:
        return PoolsCtrl(conf).makesnapshot(id)
    except InkscopeError as e:
        return Response(e.message, e.status)


@app.route('/pools/<int:id>/snapshot/<namesnapshot>', methods=['DELETE'])
@login_required
def removesnapshot(id, namesnapshot):
    try:
        return PoolsCtrl(conf).removesnapshot(id, namesnapshot)
    except InkscopeError as e:
        return Response(e.message, e.status)


#
# RBD management
#
#
# Images
#
@app.route('/RBD/images', methods=['GET'])
@login_required
def getImagesList():
    # Log.debug("Calling  RbdCtrl(conf).listImages() method")
    try:
        return Response(RbdCtrl(conf).list_images(), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


@app.route('/RBD/images/<string:pool_name>/<string:image_name>', methods=['GET'])
@login_required
def getImagesInfo(pool_name, image_name):
    # Log.debug("Calling  RbdCtrl(conf).getImagesInfo() method")
    try:
        return Response(RbdCtrl(conf).image_info(pool_name, image_name), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


@app.route('/RBD/images/<string:pool_name>/<string:image_name>', methods=['PUT'])
@login_required
def createImage(pool_name, image_name):
    # Log.debug("Calling  RbdCtrl(conf).listImages() method")
    try:
        return Response(RbdCtrl(conf).create_image(pool_name, image_name), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


@app.route('/RBD/images/<string:pool_name>/<string:image_name>/<string:action>', methods=['POST'])
@login_required
def modifyImage(pool_name, image_name , action):
    # Log.debug("Calling  RbdCtrl(conf).modifyImages() method")
    try:
        return Response(RbdCtrl(conf).modify_image(pool_name, image_name, action), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


@app.route('/RBD/images/<string:pool_name>/<string:image_name>', methods=['DELETE'])
@login_required
def deleteImage(pool_name, image_name):
    # Log.debug("Calling  RbdCtrl(conf).deleteImage() method")
    try:
        return Response(RbdCtrl(conf).delete_image(pool_name, image_name), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


#
# Snapshots
#
@app.route('/RBD/snapshots/<string:pool_name>/<string:image_name>/<string:snap_name>', methods=['GET'])
@login_required
def infoImageSnapshot(pool_name, image_name,snap_name):
    # Log.debug("Calling  RbdCtrl(conf).info_image_snapshot() method")
    try:
        return Response(RbdCtrl(conf).info_image_snapshot(pool_name, image_name, snap_name), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


@app.route('/RBD/snapshots/<string:pool_name>/<string:image_name>/<string:snap_name>', methods=['PUT'])
@login_required
def createImageSnapshot(pool_name, image_name,snap_name):
    # Log.debug("Calling  RbdCtrl(conf).create_image_snapshot() method")
    try:
        return Response(RbdCtrl(conf).create_image_snapshot(pool_name, image_name, snap_name), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


@app.route('/RBD/snapshots/<string:pool_name>/<string:image_name>/<string:snap_name>', methods=['DELETE'])
@login_required
def deleteImageSnapshot(pool_name, image_name,snap_name):
    # Log.debug("Calling  RbdCtrl(conf).delete_image_snapshot() method")
    try:
        return Response(RbdCtrl(conf).delete_image_snapshot(pool_name, image_name, snap_name), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


@app.route('/RBD/snapshots/<string:pool_name>/<string:image_name>/<string:snap_name>/<string:action>', methods=['POST'])
@login_required
def actionOnImageSnapshot(pool_name, image_name,snap_name, action):
    # print "Calling  RbdCtrl(conf).action_on_image_snapshot() method", action
    try:
        return Response(RbdCtrl(conf).action_on_image_snapshot(pool_name, image_name, snap_name, action), mimetype='application/json')
    except CalledProcessError, e:
        return Response(e.output, status=500)


#
# Probes management
#
#@app.route('/probes/<string:probe_type>/<string:probe_name>/<string:action>', methods=['POST'])
#def actionOnProbe(probe_type, probe_name, action):
    # print "Calling  probesCtrl.action_on_probe() method", action
#    try:
#        return Response(probesCtrl.action_on_probe(probe_type, probe_name, action), mimetype='application/json')
#    except CalledProcessError, e:
#        return Response(e.output, status=500)
#

#
# Osds management
#
@app.route('/osds', methods=['PUT'])
@login_required
def osds_manage(id=None):
    return OsdsCtrl(conf).osds_manage(id)


#
# Object storage management
#
# This method return a S3 Object that id is "objId".
# An exception is trhown if the object does not exist or there an issue
@app.route('/S3/object', methods=['GET'])
@login_required
def getObjectStructure():
    Log.debug("Calling  getObjectStructure() method")
    try:
        return Response(S3ObjectCtrl(conf).getObjectStructure(),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

# User management
@app.route('/S3/user', methods=['GET'])
@login_required
def listUser():
    try:
        return Response(S3Ctrl(conf).listUsers(),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user', methods=['POST'])
@login_required
def createUser():
    try:
        return Response(S3Ctrl(conf).createUser(),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>', methods=['GET'])
@login_required
def getUser(uid):
    try:
        return Response(S3Ctrl(conf).getUser(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>', methods=['PUT'])
@login_required
def modifyUser(uid):
    try:
        return Response(S3Ctrl(conf).modifyUser(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>', methods=['DELETE'])
@login_required
def removeUser(uid):
    try:
        return Response(S3Ctrl(conf).removeUser(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/user/<string:uid>/key/<string:key>', methods=['DELETE'])
@login_required
def removeUserKey(uid,key):
    try:
        return Response(S3Ctrl(conf).removeUserKey(uid,key),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/subuser', methods=['PUT'])
@login_required
def createSubuser(uid):
    try:
        return Response(S3Ctrl(conf).createSubuser(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/subuser/<string:subuser>', methods=['DELETE'])
@login_required
def deleteSubuser(uid, subuser):
    try:
        return Response(S3Ctrl(conf).deleteSubuser(uid, subuser),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/user/<string:uid>/subuser/<string:subuser>/key', methods=['PUT'])
@login_required
def createSubuserKey(uid, subuser):
    Log.debug("createSubuserKey")
    try:
        return Response(S3Ctrl(conf).createSubuserKey(uid, subuser),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/subuser/<string:subuser>/key', methods=['DELETE'])
@login_required
def deleteSubuserKey(uid, subuser):
    Log.debug("deleteSubuserKey")
    try:
        return Response(S3Ctrl(conf).deleteSubuserKey(uid, subuser),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/caps', methods=['PUT', 'POST'])
@login_required
def saveCapability(uid):
    Log.debug("saveCapability")
    try:
        return Response(S3Ctrl(conf).saveCapability(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/user/<string:uid>/caps', methods=['DELETE'])
@login_required
def deleteCapability(uid):
    Log.debug("deleteCapability")
    try:
        return Response(S3Ctrl(conf).deleteCapability(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

# bucket management

@app.route('/S3/user/<string:uid>/buckets', methods=['GET'])
@login_required
def getUserBuckets(uid,bucket=None):
    try:
        return Response(S3Ctrl(conf).getUserBuckets(uid),mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/bucket', methods=['PUT'])
@login_required
def createBucket():
    try:
        return Response(S3Ctrl(conf).createBucket(), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)


@app.route('/S3/bucket', methods=['GET'])
@login_required
def getBuckets():
    try:
        return Response(S3Ctrl(conf).getBucketInfo(None), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucket>', methods=['GET'])
@login_required
def getBucketInfo(bucket=None):
    try:
        return Response(S3Ctrl(conf).getBucketInfo(bucket), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucket>', methods=['DELETE'])
@login_required
def deleteBucket(bucket):
    try:
        return Response(S3Ctrl(conf).deleteBucket(bucket), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucket>/link', methods=['DELETE','PUT'])
@login_required
def linkBucket(bucket):
    try:
        uid = request.form['uid']
        if request.method =='PUT':
            return Response(S3Ctrl(conf).linkBucket(uid, bucket), mimetype='application/json')
        else:
            return Response(S3Ctrl(conf).unlinkBucket(uid, bucket), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/S3/bucket/<string:bucketName>/list', methods=['GET'])
@login_required
def listBucket(bucketName):
    try:
        return Response(S3Ctrl(conf).listBucket(bucketName), mimetype='application/json')
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)

@app.route('/ceph-rest-api/<regex(".+"):url>', methods=['GET', 'PUT'])
@login_required
def proxyReq(url):
    try:
        if request.method == 'GET':
            return RestProxy(conf).proxy_get(url)
        elif request.method == 'PUT':
            return RestProxy(conf).proxy_put(url)
    except S3Error , e:
        Log.err(e.__str__())
        return Response(e.reason, status=e.code)
    pass

# app.run(host='127.0.0.1', port=8081)
