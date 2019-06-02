import datetime, json, os, string, random, hashlib, base64

from flask import Flask, render_template
from flask import request
from flask import jsonify

app = Flask(__name__)

# url used for generating self links
URL = "localhost"

# read ships into dict, replace with database
def read_ships():
    file = open("static/ships.json")
    data = file.read()
    file.close()
    
    json_data = json.loads(data)
    
    return json_data

# read users into dict, replace with database
def read_users():
    file = open("static/users.json")
    data = file.read()
    file.close()
    
    json_data = json.loads(data)
    
    return json_data

# add user to database
def write_users(users):
    file = open("static/users.json", 'w')
    file.write(users)
    file.close()

# add ship to database
def write_ships(ships):
    file = open("static/ships.json", 'w')
    file.write(ships)
    file.close()

def read_ship_string():
    file = open("static/ships.json")
    data = file.read()
    file.close()
    
    return data

def decode_jwt(jwt):
    header_in = base64.b64decode(jwt.split(".")[0].encode("utf-8")+b'==')
    body_in = jwt.split(".")[1].encode("utf-8")
    signature_in = base64.b64decode(jwt.split(".")[-1].encode("utf-8")+b'==')
    
    print(body_in)
    body_in = base64.b64decode(body_in+b'==')
    
    username = json.loads(body_in)["username"]
    
    # see if profile actually exists
    users = read_users()
    exists = 0
    user_object = {}
    for user in users:
        # usernames are case insensitive
        if username.upper() == user["username"].upper():
            exists = 1
            user_object = user
    if not exists:
        return [0, "User does not exist"]
    
    # generate hashes and salts, create user entry in database
    jwt_secret = user_object["jwt_secret"]
    h_b64 = base64.b64encode(header_in)
    p_b64 = base64.b64encode(body_in)
    all_together = h_b64+p_b64+jwt_secret.encode("utf-8")
    signature = hashlib.sha256(all_together).hexdigest()
    
    # see if signatures match
    if signature_in.decode("utf-8") != signature:
        return [0, "Signature is invalid"]
    
    return [1, username]

# view a specific ship
@app.route('/ships/<string:ship_id>')
def ships(ship_id):
    ships = read_ships()
    for key in ships:
        if key["id"]==ship_id:
            return str(key).replace("'", "\"")
    return "{\"error\":\"No matching ship id\"}"

# view all ships
@app.route('/ships')
def all_ships():
    return read_ship_string()

# create a ship
@app.route('/ships', methods=['POST'])
def make_ship():
    ships = read_ships()
    # print request json
    new_ship = request.form
    
    # verify the jwt
    try:
        jwt = new_ship["jwt"]
    except:
        return "No JWT provided", 401
    username = decode_jwt(jwt)
    if username[0] == 0:
        return "Invalid JWT", 401
        
    username = username[-1]
    
    # check all old attributes that must me unique
    for key in ships:
        if new_ship['name']==key['name']:
            return "{\"error\":\"ship name already exists\"}"
    ship_temp = {}
    # generate random id
    ship_temp["id"] = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
    ship_temp["name"] = new_ship['name']
    ship_temp["type"] = new_ship['type']
    ship_temp["owner"] = username
    ship_temp["length"] = new_ship['length']
    
    # create self link
    self_link = URL+"/ships/"+ship_temp["id"]
    ship_temp["self"] = self_link
    
    # add the ship to the "database"
    ships.append(ship_temp)
    write_ships(json.dumps(ships))
    
    print(str(ship_temp).replace("'", "\""))
    
    return str(ship_temp).replace("'", "\"")

# delete a ship
@app.route('/ships/<string:ship_id>', methods=['DELETE'])
def delete_ship(ship_id):
    new_ship = request.form
    # verify the jwt
    try:
        jwt = new_ship["jwt"]
    except:
        return "No JWT provided", 401
    username = decode_jwt(jwt)
    if username[0] == 0:
        return "Invalid JWT", 401
        
    username = username[-1]

    ships = read_ships()
    index = 0
    for key in ships:
        if key["id"]==ship_id:
            if key["owner"] != username:
                return "You cannot delete other user's ships", 403
            # remove the ship, verify it belongs to user
            tmp = ships[index]
            ships.pop(index)
            write_ships(json.dumps(ships))
            return "{\"Success\":\"ship deleted\"}"
            
        index+=1
    return "{\"error\":\"No matching ship id\"}"

@app.route('/users/<string:user_name>/ships', methods=['GET'])
def view_ship(user_name):
    new_ship = request.form
    # verify the jwt
    try:
        jwt = new_ship["jwt"]
    except:
        return "No JWT provided", 401
    username = decode_jwt(jwt)
    if username[0] == 0:
        return "Invalid JWT", 401
        
    username = username[-1]
    if username.upper() != user_name.upper():
        return "You cannot see another user's ships", 403
    
    ship_list = []
    ships = read_ships()
    for key in ships:
        if key["owner"]==username:
            ship_list.append(key)
    return json.dumps(ship_list)

@app.route('/')
def root():
    homepage_file = "static/homepage.html"
    file = open(homepage_file)
    page = file.read()
    file.close()
    
    return page

@app.route('/create_user')
def create_user():
    homepage_file = "static/create_user.html"
    file = open(homepage_file)
    page = file.read()
    file.close()
    
    return page

@app.route('/create_user', methods=['POST'])
def create_user_post():
    post_stuff = request.form
    
    print(post_stuff)
    
    # compare passwords to make sure they match
    if post_stuff["password1"] != post_stuff["password2"]:
        return "Passwords do not match, please <a href=\"/create_user\">try again.</a>"
    
    # make sure the username is not taken
    users = read_users()
    for user in users:
        # usernames are case insensitive
        if post_stuff["username"].upper() == user["username"].upper():
            return "That username is already taken, please <a href=\"/create_user\">try again.</a>"
    
    # generate hashes and salts, create user entry in database
    salt = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(5)])
    jwt_secret = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])
    pass_and_salt = post_stuff["password1"]+salt
    sha256 = hashlib.sha256(pass_and_salt.encode()).hexdigest()
    
    # create jwt
    header = '''{"alg": "SHA256", "typ": "JWT"}'''
    payload = "{\"username\": \""+post_stuff["username"]+"\"}"
    
    h_b64 = base64.b64encode(header.encode("utf-8"))
    p_b64 = base64.b64encode(payload.encode("utf-8"))
    all_together = h_b64+p_b64+jwt_secret.encode("utf-8")
    
    signature = hashlib.sha256(all_together).hexdigest()
    signature_b64 = base64.b64encode(signature.encode("utf-8"))
    
    jwt = h_b64+".".encode("utf-8")+p_b64+".".encode("utf-8")+signature_b64
    
    user_temp = {}
    user_temp["username"] = post_stuff["username"]
    user_temp["hash"] = sha256
    user_temp["salt"] = salt
    user_temp["jwt_secret"] = jwt_secret
    user_temp["jwt"] = jwt.decode("utf-8").replace("==", "")
    
    users.append(user_temp)
    write_users(json.dumps(users))
    
    return "Success! <a href=\"/\">Login</a> with your account.<br><br>"

@app.route('/', methods=['POST'])
def login():
    post_stuff = request.form
    
    # see if user exists
    users = read_users()
    
    print(post_stuff["password"])
    
    user_object = {}
    not_present = True
    for user in users:
        # usernames are case insensitive
        if post_stuff["username"].upper() == user["username"].upper():
            not_present = False
            user_object = user
    
    if not_present:
        return "Username or password incorrect, please <a href=\"/\">try again.</a>"
    
    # create and compare sha256 hash
    pass_and_salt = post_stuff["password"]+user["salt"]
    sha256 = hashlib.sha256(pass_and_salt.encode()).hexdigest()
    if sha256 != user["hash"]:
        return "Username or password incorrect, please <a href=\"/\">try again.</a>"
    
    user_page = "Success!<br><br>Your JWT: "+user["jwt"]
    
    return user_page

if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='0.0.0.0', port=8080, debug=True)
