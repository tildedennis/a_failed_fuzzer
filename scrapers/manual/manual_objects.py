fp = open("objects", "rb")
objects = [l.strip() for l in fp.readlines() if not l.startswith("#")]
fp.close()

fp = open("object_methods", "rb")
methods = [l.strip() for l in fp.readlines() if not l.startswith("#")]
fp.close()

fp = open("object_properties", "rb")
properties = [l.strip() for l in fp.readlines() if not l.startswith("#")]
fp.close()

for obj in objects:
    for method in methods:
        print "%s,method,%s" % (obj, method)

    for obj_property in properties:
        print "%s,property,%s" % (obj, obj_property)
