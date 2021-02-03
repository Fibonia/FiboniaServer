# from hashids import Hashids

# #mvaiyn3

# letters = {'a':1, 'b':2, 'c':3, 'd':4, 'e':5, 'f':6, 'g':7, 'h':8, 'i':9, 'j':10, 'k':11,
#             'l':12, 'm':13, 'n':14, 'o':15, 'p':16, 'q':17, 'r':18, 's':19, 't':20, 'u':21,
#             'v':22, 'w':23, 'x':24, 'y':25, 'z':26}

#     #Converts name (string) to int to use it as the parameter input for the hashid function
# def alpha_to_num(name):
#     sum = 0
#     count = 0
#     name = ''.join(c.lower() for c in name if not c.isspace())
#     for i in name:
#         if count % 2 == 0:
#             sum += letters.get(i)
#         else: 
#             sum *= letters.get(i)
#         count += 1
#     return sum
# hashids = Hashids(min_length=7, alphabet='abcdefghijklmnopqrstuvwxyz0123456789', salt = 'fibonia')

# #numerical encoding of the name
# num = alpha_to_num('zechariah kim')
# #encode


# hashid = hashids.encrypt(num)
# print(hashid)
# decrypted = hashids.decrypt(hashid)
# print(type(decrypted))

import pymongo

mongo_url = "mongodb+srv://gurk91:Fibonia!2345@cluster0.a5ggi.mongodb.net/test?retryWrites=true&w=majority"
client = pymongo.MongoClient(mongo_url, ssl=True,ssl_cert_reqs=ssl.CERT_NONE)
mg_db = client.get_database('FibTest')

def addData():
    data = request.json["value"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    table.insert_one(data)
    return "Data Inserted"

def deleteData():
    ourid = request.json["id"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    myquery = {"_id":ObjectId(ourid)}
    table.delete_one(myquery)
    return "Data Deleted"

def selectData():
    ourid = request.json["id"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    myquery = {"_id":ObjectId(ourid)}
    mydoc = table.find(myquery)
    list_cur = list(mydoc)
    mydoc = dumps(list_cur)
    return mydoc

def updateData():
    ourid = request.json["id"]
    value = request.json["value"]
    ourstr = "mg_db."+request.json["collection"]
    table = eval(ourstr)
    myquery = {"_id":ObjectId(ourid)}
    newvalues = { "$set": value }
    table.update_one(myquery,newvalues)
    return "Data Updated"