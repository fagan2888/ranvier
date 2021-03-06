# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Miscallenious useful generic resource classes.
"""

# ranvier imports
from ranvier.resource import Resource
from ranvier import _verbosity, RanvierError


__all__ = ('LeafResource', 'DelegatorResource',
           'VarResource', 'VarVarResource', 'VarDelegatorResource',
           'RedirectResource', 'LogRequests', 'RemoveBase')



class LeafResource(Resource):
    """
    Base class for all leaf resources.
    """
    def enum_targets(self, enumrator):
##         super(LeafResource, self).enum_targets(enumrator)

        # Declare the node a leaf.
        enumrator.declare_target()

    def handle_base(self, ctxt):
        # Just check that this resource is a leaf before calling the handler.
        if not ctxt.locator.isleaf():
            return ctxt.response.errorNotFound()

        return Resource.handle_base(self, ctxt)



class DelegatorResource(Resource):
    """
    Resource base class for resources which do something and then
    unconditionally forward to another resource.  It uses a template method to
    implement this simple behaviour.
    """
    def __init__(self, next_resource, **kwds):
        Resource.__init__(self, **kwds)
        self._next = next_resource

    def getnext(self):
        return self._next

    def enum_targets(self, enumrator):
##         super(DelegatorResource, self).enum_targets(enumrator)

        enumrator.branch_anon(self._next)

    def handle_base(self, ctxt):
        # Call the handler.
        rcode = Resource.handle_base(self, ctxt)

        # Support errors that does not use exception handling.  Typically it
        # would be better to raise an exception to unwind the chain of
        # responsibility, but I'm not one to decide what you like to do.  This
        # is all about flexibility.
        if rcode is not None:
            return True

        # Automatically forward to the delegate resource if there are no
        # errors.
        try:
            r = self.delegate(self._next, ctxt)
        finally:
            self.post_handle(ctxt)
            
        return r

    def post_handle(self, ctxt):
        """
        Callback that can be overriden to perform stuff after the request has
        been delegated.  This is called even if when unwinding from an
        exception.
        """
        # Noop.
        


class VarResource(LeafResource):
    """
    Resource base class that unconditionally consumes one path component and
    that serves as a leaf.
    """
    def __init__(self, compname, compfmt=None, **kwds):
        """
        'compname': if specified, we store the component under an attribute with
                    this name in the context.
        """
        LeafResource.__init__(self, **kwds)

        assert isinstance(compname, str)
        self.compname = compname
        """The name of the attribute to store the component as."""

        self.compfmt = compfmt
        """The format of the component, if any."""

    def enum_targets(self, enumrator):
        enumrator.declare_target(self.compname, format=self.compfmt)

    def consume_component(self, ctxt):
        if _verbosity >= 1:
            ctxt.response.log("resolver: %s" %
                              ctxt.locator.path[ctxt.locator.index:])

        # Make sure we're not at the leaf.
        if ctxt.locator.isleaf():
            return ctxt.response.errorNotFound()
        
        # Get the name of the current component.
        comp = ctxt.locator.current()
        
        # Store the component value in the context.
        if hasattr(ctxt, self.compname):
            raise RanvierError("Error: Context already has attribute '%s'." %
                               self.compname)
        setattr(ctxt, self.compname, comp)

        # Consume the component.
        ctxt.locator.next()

    def handle_base(self, ctxt):
        self.consume_component(ctxt)
        return Resource.handle_base(self, ctxt)

    handle = Resource.handle_nofail


class VarVarResource(VarResource):
    """
    Resource class that consumes 0 to all path components and that serves as a
    leaf.  The stored value is a list of the consumed components.
    """

    def consume_component(self, ctxt):
        if _verbosity >= 1:
            ctxt.response.log("resolver: %s" %
                              ctxt.locator.path[ctxt.locator.index:])

        # Get the rest of the components.
        loc = ctxt.locator
        comps = []
        while not loc.isleaf():
            comps.append(loc.current())
            loc.next()
        
        # Store the component values in the context.
        if hasattr(ctxt, self.compname):
            raise RanvierError("Error: Context already has attribute '%s'." %
                               self.compname)
        setattr(ctxt, self.compname, comps)


class VarDelegatorResource(DelegatorResource, VarResource):
    """
    Resource base class that unconditionally consumes one path component and
    that forwards to another resource.  This resource does not allow being a
    leaf (this would be possible, you could implement that if desired).

    If you need to perform some validation, override the handle() method and
    signal an error if your check fails.  The component has been set on the
    context object.
    """
    def __init__(self, compname, next_resource, **kwds):
        """
        'compname': if specified, we store the component under an attribute with
                    this name in the context.
        """
        VarResource.__init__(self, compname, **kwds)
        DelegatorResource.__init__(self, next_resource, **kwds)

    def enum_targets(self, enumrator):
##         super(VarDelegatorResource, self).enum_targets(enumrator)

        enumrator.branch_var(self.compname, self.getnext())

    def handle_base(self, ctxt):
        self.consume_component(ctxt)
        return DelegatorResource.handle_base(self, ctxt)

    handle = Resource.handle_nofail



class RedirectResource(LeafResource):
    """
    Simply redirect to a fixed location, identified by a resource-id.  This uses
    the mapper in the context to map the target to an URL.
    """
    def __init__(self, targetid, *args, **kwds):
        LeafResource.__init__(self, **kwds)
        self.targetid = targetid
        self.args = args

    def handle(self, ctxt):
        target = ctxt.mapurl(self.targetid, *self.args)
        ctxt.response.redirect(target)



class LogRequests(DelegatorResource):
    """
    Log a header to the error file and delegate.
    """

    fmt = '----------------------------- %s'

    def handle(self, ctxt):
        ctxt.response.log(self.fmt % ctxt.locator.uri())



class RemoveBase(DelegatorResource):
    """
    Resource that removes a fixed number of base components.

    This is rather deprecated.  Instead of using this, you should use the
    URLMapper's 'rootloc' option.
    """
    def __init__(self, count, nextres, **kwds):
        DelegatorResource.__init__(self, nextres, **kwds)
        self.count = count

    def handle(self, ctxt):
        for c in xrange(self.count):
            ctxt.locator.next()


