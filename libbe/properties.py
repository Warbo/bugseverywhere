# Bugs Everywhere - a distributed bugtracker
# Copyright (C) 2008 W. Trevor King <wking@drexel.edu>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module provides a series of useful decorators for defining
various types of properties.  For example usage, consider the
unittests at the end of the module.

See
  http://www.python.org/dev/peps/pep-0318/
and
  http://www.phyast.pitt.edu/~micheles/python/documentation.html
for more information on decorators.
"""

import unittest


class ValueCheckError (ValueError):
    def __init__(self, name, value, allowed):
        msg = "%s not in %s for %s" % (value, allowed, name)
        ValueError.__init__(self, msg)
        self.name = name
        self.value = value
        self.allowed = allowed

def Property(funcs):
    """
    End a chain of property decorators, returning a property.
    """
    args = {}
    args["fget"] = funcs.get("fget", None)
    args["fset"] = funcs.get("fset", None)
    args["fdel"] = funcs.get("fdel", None)
    args["doc"] = funcs.get("doc", None)
    
    #print "Creating a property with"
    #for key, val in args.items(): print key, value
    return property(**args)

def doc_property(doc=None):
    """
    Add a docstring to a chain of property decorators.
    """
    def decorator(funcs=None):
        """
        Takes either a dict of funcs {"fget":fnX, "fset":fnY, ...}
        or a function fn() returning such a dict.
        """
        if hasattr(funcs, "__call__"):
            funcs = funcs() # convert from function-arg to dict
        funcs["doc"] = doc
        return funcs
    return decorator

def local_property(name, null=None):
    """
    Define get/set access to per-parent-instance local storage.  Uses
    ._<name>_value to store the value for a particular owner instance.
    If the ._<name>_value attribute does not exist, returns null.
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget", None)
        fset = funcs.get("fset", None)
        def _fget(self):
            if fget is not None:
                fget(self)
            value = getattr(self, "_%s_value" % name, null)
            return value
        def _fset(self, value):
            setattr(self, "_%s_value" % name, value)
            if fset is not None:
                fset(self, value)
        funcs["fget"] = _fget
        funcs["fset"] = _fset
        funcs["name"] = name
        return funcs
    return decorator

def settings_property(name, null=None):
    """
    Similar to local_property, except where local_property stores the
    value in instance._<name>_value, settings_property stores the
    value in instance.settings[name].
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget", None)
        fset = funcs.get("fset", None)
        def _fget(self):
            if fget is not None:
                fget(self)
            value = self.settings.get(name, null)
            return value
        def _fset(self, value):
            self.settings[name] = value
            if fset is not None:
                fset(self, value)
        funcs["fget"] = _fget
        funcs["fset"] = _fset
        funcs["name"] = name
        return funcs
    return decorator

def defaulting_property(default=None, null=None):
    """
    Define a default value for get access to a property.
    If the stored value is null, then default is returned.
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget")
        def _fget(self):
            value = fget(self)
            if value == null:
                return default
            return value
        funcs["fget"] = _fget
        return funcs
    return decorator

def fn_checked_property(value_allowed_fn):
    """
    Define allowed values for get/set access to a property.
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget")
        fset = funcs.get("fset")
        name = funcs.get("name", "<unknown>")
        def _fget(self):
            value = fget(self)
            if value_allowed_fn(value) != True:
                raise ValueCheckError(name, value, value_allowed_fn)
            return value
        def _fset(self, value):
            if value_allowed_fn(value) != True:
                raise ValueCheckError(name, value, value_allowed_fn)
            fset(self, value)
        funcs["fget"] = _fget
        funcs["fset"] = _fset
        return funcs
    return decorator

def checked_property(allowed=[]):
    """
    Define allowed values for get/set access to a property.
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget")
        fset = funcs.get("fset")
        name = funcs.get("name", "<unknown>")
        def _fget(self):
            value = fget(self)
            if value not in allowed:
                raise ValueCheckError(name, value, allowed)
            return value
        def _fset(self, value):
            if value not in allowed:
                raise ValueCheckError(name, value, allowed)
            fset(self, value)
        funcs["fget"] = _fget
        funcs["fset"] = _fset
        return funcs
    return decorator

def cached_property(generator, initVal=None):
    """
    Allow caching of values generated by generator(instance), where
    instance is the instance to which this property belongs.  Uses
    ._<name>_cache to store a cache flag for a particular owner
    instance.

    When the cache flag is True or missing and the stored value is
    initVal, the first fget call triggers the generator function,
    whiose output is stored in _<name>_cached_value.  That and
    subsequent calls to fget will return this cached value.

    If the input value is no longer initVal (e.g. a value has been
    loaded from disk or set with fset), that value overrides any
    cached value, and this property has no effect.
    
    When the cache flag is False and the stored value is initVal, the
    generator is not cached, but is called on every fget.

    The cache flag is missing on initialization.  Particular instances
    may override by setting their own flag.
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget")
        fset = funcs.get("fset")
        name = funcs.get("name", "<unknown>")
        def _fget(self):
            cache = getattr(self, "_%s_cache" % name, True)
            value = fget(self)
            if cache == True:
                if value == initVal:
                    if hasattr(self, "_%s_cached_value" % name):
                        value = getattr(self, "_%s_cached_value" % name)
                    else:
                        value = generator(self)
                        setattr(self, "_%s_cached_value" % name, value)
            else:
                if value == initVal:
                    value = generator(self)
            return value
        funcs["fget"] = _fget
        return funcs
    return decorator

def primed_property(primer, initVal=None):
    """
    Just like a generator_property, except that instead of returning a
    new value and running fset to cache it, the primer performs some
    background manipulation (e.g. loads data into instance.settings)
    such that a _second_ pass through fget succeeds.

    The 'cache' flag becomes a 'prime' flag, with priming taking place
    whenever ._<name>_prime is True, or is False or missing and
    value == initVal.
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget")
        name = funcs.get("name", "<unknown>")
        def _fget(self):
            prime = getattr(self, "_%s_prime" % name, False)
            if prime == False:
                value = fget(self)
            if prime == True or (prime == False and value == initVal):
                primer(self)
                value = fget(self)
            return value
        funcs["fget"] = _fget
        return funcs
    return decorator

def change_hook_property(hook):
    """
    Call the function hook(instance, old_value, new_value) whenever a
    value different from the current value is set (instance is a a
    reference to the class instance to which this property belongs).
    This is useful for saving changes to disk, etc.
    """
    def decorator(funcs):
        if hasattr(funcs, "__call__"):
            funcs = funcs()
        fget = funcs.get("fget")
        fset = funcs.get("fset")
        name = funcs.get("name", "<unknown>")
        def _fset(self, value):
            old_value = fget(self)
            if value != old_value:
                hook(self, old_value, value)
            fset(self, value)
        funcs["fset"] = _fset
        return funcs
    return decorator


class DecoratorTests(unittest.TestCase):
    def testLocalDoc(self):
        class Test(object):
            @Property
            @doc_property("A fancy property")
            def x():
                return {}
        self.failUnless(Test.x.__doc__ == "A fancy property",
                        Test.x.__doc__)
    def testLocalProperty(self):
        class Test(object):
            @Property
            @local_property(name="LOCAL")
            def x():
                return {}
        t = Test()
        self.failUnless(t.x == None, str(t.x))
        t.x = 'z' # the first set initializes ._LOCAL_value
        self.failUnless(t.x == 'z', str(t.x))
        self.failUnless("_LOCAL_value" in dir(t), dir(t))
        self.failUnless(t._LOCAL_value == 'z', t._LOCAL_value)
    def testSettingsProperty(self):
        class Test(object):
            @Property
            @settings_property(name="attr")
            def x():
                return {}
            def __init__(self):
                self.settings = {}
        t = Test()
        self.failUnless(t.x == None, str(t.x))
        t.x = 'z' # the first set initializes ._LOCAL_value
        self.failUnless(t.x == 'z', str(t.x))
        self.failUnless("attr" in t.settings, t.settings)
        self.failUnless(t.settings["attr"] == 'z', t.settings["attr"])
    def testDefaultingLocalProperty(self):
        class Test(object):
            @Property
            @defaulting_property(default='y', null='x')
            @local_property(name="DEFAULT")
            def x(): return {}
        t = Test()
        self.failUnless(t.x == None, str(t.x)) 
        t.x = 'x'
        self.failUnless(t.x == 'y', str(t.x))
        t.x = 'y'
        self.failUnless(t.x == 'y', str(t.x))
        t.x = 'z'
        self.failUnless(t.x == 'z', str(t.x))
    def testCheckedLocalProperty(self):
        class Test(object):
            @Property
            @checked_property(allowed=['x', 'y', 'z'])
            @local_property(name="CHECKED")
            def x(): return {}
            def __init__(self):
                self._CHECKED_value = 'x'
        t = Test()
        self.failUnless(t.x == 'x', str(t.x))
        try:
            t.x = None
            e = None
        except ValueCheckError, e:
            pass
        self.failUnless(type(e) == ValueCheckError, type(e))
    def testTwoCheckedLocalProperties(self):
        class Test(object):
            @Property
            @checked_property(allowed=['x', 'y', 'z'])
            @local_property(name="X")
            def x(): return {}

            @Property
            @checked_property(allowed=['a', 'b', 'c'])
            @local_property(name="A")
            def a(): return {}
            def __init__(self):
                self._A_value = 'a'
                self._X_value = 'x'
        t = Test()
        try:
            t.x = 'a'
            e = None
        except ValueCheckError, e:
            pass
        self.failUnless(type(e) == ValueCheckError, type(e))
        t.x = 'x'
        t.x = 'y'
        t.x = 'z'
        try:
            t.a = 'x'
            e = None
        except ValueCheckError, e:
            pass
        self.failUnless(type(e) == ValueCheckError, type(e))
        t.a = 'a'
        t.a = 'b'
        t.a = 'c'
    def testFnCheckedLocalProperty(self):
        class Test(object):
            @Property
            @fn_checked_property(lambda v : v in ['x', 'y', 'z'])
            @local_property(name="CHECKED")
            def x(): return {}
            def __init__(self):
                self._CHECKED_value = 'x'
        t = Test()
        self.failUnless(t.x == 'x', str(t.x))
        try:
            t.x = None
            e = None
        except ValueCheckError, e:
            pass
        self.failUnless(type(e) == ValueCheckError, type(e))
    def testCachedLocalProperty(self):
        class Gen(object):
            def __init__(self):
                self.i = 0
            def __call__(self, owner):
                self.i += 1
                return self.i
        class Test(object):
            @Property
            @cached_property(generator=Gen(), initVal=None)
            @local_property(name="CACHED")
            def x(): return {}
        t = Test()
        self.failIf("_CACHED_cache" in dir(t), getattr(t, "_CACHED_cache", None))
        self.failUnless(t.x == 1, t.x)
        self.failUnless(t.x == 1, t.x)
        self.failUnless(t.x == 1, t.x)
        t.x = 8
        self.failUnless(t.x == 8, t.x)
        self.failUnless(t.x == 8, t.x)
        t._CACHED_cache = False        # Caching is off, but the stored value
        val = t.x                      # is 8, not the initVal (None), so we
        self.failUnless(val == 8, val) # get 8.
        t._CACHED_value = None         # Now we've set the stored value to None
        val = t.x                      # so future calls to fget (like this)
        self.failUnless(val == 2, val) # will call the generator every time...
        val = t.x
        self.failUnless(val == 3, val)
        val = t.x
        self.failUnless(val == 4, val)
        t._CACHED_cache = True              # We turn caching back on, and get
        self.failUnless(t.x == 1, str(t.x)) # the original cached value.
        del t._CACHED_cached_value          # Removing that value forces a
        self.failUnless(t.x == 5, str(t.x)) # single cache-regenerating call
        self.failUnless(t.x == 5, str(t.x)) # to the genenerator, after which
        self.failUnless(t.x == 5, str(t.x)) # we get the new cached value.
    def testPrimedLocalProperty(self):
        class Test(object):
            def prime(self):
                self.settings["PRIMED"] = "initialized"
            @Property
            @primed_property(primer=prime, initVal=None)
            @settings_property(name="PRIMED")
            def x(): return {}
            def __init__(self):
                self.settings={}
        t = Test()
        self.failIf("_PRIMED_prime" in dir(t), getattr(t, "_PRIMED_prime", None))
        self.failUnless(t.x == "initialized", t.x)
        t.x = 1
        self.failUnless(t.x == 1, t.x)
        t.x = None
        self.failUnless(t.x == "initialized", t.x)
        t._PRIMED_prime = True
        t.x = 3
        self.failUnless(t.x == "initialized", t.x)
        t._PRIMED_prime = False
        t.x = 3
        self.failUnless(t.x == 3, t.x)
    def testChangeHookLocalProperty(self):
        class Test(object):
            def _hook(self, old, new):
                self.old = old
                self.new = new

            @Property
            @change_hook_property(_hook)
            @local_property(name="HOOKED")
            def x(): return {}
        t = Test()
        t.x = 1
        self.failUnless(t.old == None, t.old)
        self.failUnless(t.new == 1, t.new)
        t.x = 1
        self.failUnless(t.old == None, t.old)
        self.failUnless(t.new == 1, t.new)
        t.x = 2
        self.failUnless(t.old == 1, t.old)
        self.failUnless(t.new == 2, t.new)

suite = unittest.TestLoader().loadTestsFromTestCase(DecoratorTests)
