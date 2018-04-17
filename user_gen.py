import hashlib, uuid
salt = uuid.uuid4().hex
print('{}:{}'.format(hashlib.sha512(input('enter password:').encode() + salt.encode()).hexdigest(), salt))
