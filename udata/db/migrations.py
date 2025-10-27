"""
Data migrations logic
"""

import importlib.util
import inspect
import logging
import os
import queue
import traceback
from datetime import datetime
from logging.handlers import QueueHandler

from mongoengine.connection import get_db
from pymongo import ReturnDocument

log = logging.getLogger(__name__)


class MigrationError(Exception):
    """
    Raised on migration execution error.

    :param msg str: A human readable message (a reason)
    :param output str: An optionnal array of logging output
    :param exc Exception: An optionnal underlying exception
    """

    def __init__(self, msg, output=None, exc=None, traceback=None):
        super().__init__(msg)
        self.msg = msg
        self.output = output
        self.exc = exc
        self.traceback = traceback


class RollbackError(MigrationError):
    """
    Raised on rollback.
    Hold the initial migration error and rollback exception (if any)
    """

    def __init__(self, msg, output=None, exc=None, migrate_exc=None):
        super().__init__(msg)
        self.msg = msg
        self.output = output
        self.exc = exc
        self.migrate_exc = migrate_exc


class MigrationFormatter(logging.Formatter):
    pass


class Record(dict):
    """
    A simple wrapper to migrations document
    """

    __getattr__ = dict.get

    def load(self):
        specs = {"filename": self["filename"]}
        self.clear()
        data = get_db().migrations.find_one(specs)
        self.update(data or specs)

    def exists(self):
        return bool(self._id)

    def __bool__(self):
        return self.exists()

    @property
    def collection(self):
        return get_db().migrations

    @property
    def status(self):
        """
        Status is the status of the last operation.

        Will be `None` if the record doesn't exists.
        Possible values are:
          - success
          - rollback
          - rollback-error
          - error
          - recorded
        """
        if not self.exists():
            return
        op = self.ops[-1]
        if op["success"]:
            if op["type"] == "migrate":
                return "success"
            elif op["type"] == "rollback":
                return "rollback"
            elif op["type"] == "record":
                return "recorded"
            else:
                return "unknown"
        else:
            return "rollback-error" if op["type"] == "rollback" else "error"

    @property
    def last_date(self):
        if not self.exists():
            return
        op = self.ops[-1]
        return op["date"]

    @property
    def ok(self):
        """
        Is true if the migration is considered as successfully applied
        """
        if not self.exists():
            return False
        op = self.ops[-1]
        return op["success"] and op["type"] in ("migrate", "record")

    def add(self, _type, migration, output, state, success):
        script = inspect.getsource(migration)
        return Record(
            self.collection.find_one_and_update(
                {"filename": self.filename},
                {
                    "$push": {
                        "ops": {
                            "date": datetime.utcnow(),
                            "type": _type,
                            "script": script,
                            "output": output,
                            "state": state,
                            "success": success,
                        }
                    }
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        )

    def delete(self):
        return self.collection.delete_one({"_id": self._id})


class Migration:
    def __init__(self, filename):
        if not filename.endswith(".py"):
            filename += ".py"

        self.filename = filename
        self._record = None
        self._module = None

    @property
    def collection(self):
        return get_db().migrations

    @property
    def db_query(self):
        return {"filename": self.filename}

    @property
    def label(self):
        return self.filename

    @property
    def record(self):
        if self._record is None:
            specs = {"filename": self.filename}
            data = get_db().migrations.find_one(specs)
            self._record = Record(data or specs)
        return self._record

    @property
    def module(self):
        if self._module is None:
            self._module = load_migration(self.filename)
        return self._module

    def __eq__(self, value):
        return isinstance(value, Migration) and getattr(value, "filename") == self.filename

    def execute(self, recordonly=False, dryrun=False):
        """
        Execute a migration

        If recordonly is True, the migration is only recorded
        If dryrun is True, the migration is neither executed nor recorded
        """
        q = queue.Queue(-1)  # no limit on size
        handler = QueueHandler(q)
        handler.setFormatter(MigrationFormatter())
        logger = getattr(self.module, "log", logging.getLogger(self.module.__name__))
        logger.propagate = False
        for h in logger.handlers:
            logger.removeHandler(h)
        logger.addHandler(handler)

        if not hasattr(self.module, "migrate"):
            error = SyntaxError("A migration should at least have a migrate(db) function")
            raise MigrationError("Error while executing migration", exc=error)

        out = [["info", "Recorded only"]] if recordonly else []
        state = {}

        if not recordonly and not dryrun:
            db = get_db()
            db._state = state
            try:
                self.module.migrate(db)
                out = _extract_output(q)
            except Exception as e:
                out = _extract_output(q)
                tb = traceback.format_exc()
                self.add_record("migrate", out, db._state, False, traceback=tb)
                fe = MigrationError(
                    "Error while executing migration", output=out, exc=e, traceback=tb
                )
                if hasattr(self.module, "rollback"):
                    try:
                        self.module.rollback(db)
                        out = _extract_output(q)
                        self.add_record("rollback", out, db._state, True)
                        msg = "Error while executing migration, rollback has been applied"
                        fe = RollbackError(msg, output=out, migrate_exc=fe)
                    except Exception as re:
                        out = _extract_output(q)
                        self.add_record("rollback", out, db._state, False)
                        msg = "Error while executing migration rollback"
                        fe = RollbackError(msg, output=out, exc=re, migrate_exc=fe)
                raise fe

        if not dryrun:
            self.add_record("migrate", out, state, True)

        return out

    def unrecord(self):
        """Delete a migration record"""
        if not self.record.exists():
            return False
        return bool(self.collection.delete_one(self.db_query).deleted_count)

    def add_record(self, type, output, state, success, traceback=None):
        script = inspect.getsource(self.module)
        return Record(
            self.collection.find_one_and_update(
                self.db_query,
                {
                    "$push": {
                        "ops": {
                            "date": datetime.utcnow(),
                            "type": type,
                            "script": script,
                            "output": output,
                            "state": state,
                            "success": success,
                            "traceback": traceback,
                        }
                    }
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        )


def get(filename):
    """Get a migration"""
    return Migration(filename)


def list_available():
    """
    List available migrations from udata/migrations

    Returns a list of Migration objects sorted by filename
    """
    from importlib.resources import files

    migrations_path = files("udata").joinpath("migrations")

    migrations = [Migration(item.name) for item in migrations_path.iterdir() if item.is_file()]

    return sorted(migrations, key=lambda m: m.filename)


def load_migration(filename):
    """
    Load a migration from its python file

    :returns: the loaded module
    """
    from importlib.resources import files

    basename = os.path.splitext(os.path.basename(filename))[0]
    name = f"udata.migrations.{basename}"

    try:
        script = files("udata").joinpath("migrations", filename).read_bytes()
    except Exception:
        msg = f"Unable to load file {filename}"
        raise MigrationError(msg)

    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(script, module.__dict__)
    module.__file__ = str(files("udata").joinpath("migrations", filename))
    return module


def _extract_output(q):
    """Extract log output from a QueueHandler queue"""
    out = []
    while not q.empty():
        record = q.get()
        # Use list instead of tuple to have the same data before and after mongo persist
        out.append([record.levelname.lower(), record.getMessage()])
    return out
