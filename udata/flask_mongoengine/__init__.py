"""
This module is a copy-paste of the components we use from flask-mongoengine.

The original flask-mongoengine project (https://github.com/MongoEngine/flask-mongoengine/)
is no longer maintained. While there are some forks like
https://github.com/idoshr/flask-mongoengine, they don't seem to work well and also
appear to be poorly maintained.

Since we want to be able to update Flask and flask-mongoengine is a blocking dependency
for the upgrade, we decided to internalize it. There isn't much code, and we should also
be able to simplify this implementation as we simplify udata over time.
"""
