"""Upgrade the bugs to the latest format"""
import os.path
import errno
from libbe import bugdir, rcs

def execute(args):
    root = bugdir.tree_root(".", old_version=True)
    for uuid in root.list_uuids():
        old_bug = OldBug(root.bugs_path, uuid)
        
        new_bug = bugdir.Bug(root.bugs_path, None)
        new_bug.uuid = old_bug.uuid
        new_bug.summary = old_bug.summary
        new_bug.creator = old_bug.creator
        new_bug.target = old_bug.target
        new_bug.status = old_bug.status
        new_bug.severity = old_bug.severity

        new_bug.save()
    for uuid in root.list_uuids():
        old_bug = OldBug(root.bugs_path, uuid)
        old_bug.delete()

    bugdir.set_version(root.dir)

def file_property(name, valid=None):
    def getter(self):
        value = self._get_value(name) 
        if valid is not None:
            if value not in valid:
                raise InvalidValue(name, value)
        return value
    def setter(self, value):
        if valid is not None:
            if value not in valid and value is not None:
                raise InvalidValue(name, value)
        return self._set_value(name, value)
    return property(getter, setter)


class OldBug(object):
    def __init__(self, path, uuid):
        self.path = os.path.join(path, uuid)
        self.uuid = uuid

    def get_path(self, file):
        return os.path.join(self.path, file)

    summary = file_property("summary")
    creator = file_property("creator")
    target = file_property("target")
    status = file_property("status", valid=("open", "closed"))
    severity = file_property("severity", valid=("wishlist", "minor", "serious",
                                                "critical", "fatal"))
    def delete(self):
        self.summary = None
        self.creator = None
        self.target = None
        self.status = None
        self.severity = None
        self._set_value("name", None)

    def _get_active(self):
        return self.status == "open"

    active = property(_get_active)

    def _get_value(self, name):
        try:
            return file(self.get_path(name), "rb").read().rstrip("\n")
        except IOError, e:
            if e.errno == errno.EEXIST:
                return None

    def _set_value(self, name, value):
        if value is None:
            try:
                rcs.unlink(self.get_path(name))
            except OSError, e:
                if e.errno != 2:
                    raise
        else:
            rcs.set_file_contents(self.get_path(name), "%s\n" % value)



