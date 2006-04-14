#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
#
# $Source: /home/blais/repos/cvsroot/hume/app/lib/hume/resources/pseudores.py,v $
# $Id: pseudores.py,v 1.2 2005/06/29 14:51:54 blais Exp $
#

"""
Pseudo resources, which use a path component as an argument for some action.
"""

# stdlib imports
import types, re

# hume imports
from hume import resource, response, authentication, logger
from hume import umusers, umprivileges
from hume.resources.umres import login_redirect


class Redirect(resource.Resource):
    """
    Simply redirect to a fixed location.
    """
    def __init__( self, target, **kdws ):
        Resource.__init__(self, **kwds)
        self._target = target

    def handle( self, ctxt ):
        response.redirect(self._target)


class RequireAuth(resource.Resource):
    """
    A handler which requires authentication to follow the request.
    """
    def __init__( self, nextres, **kwds ):
        resource.Resource.__init__(self, **kwds)
        self._nextres = nextres

    def enum( self, enumv ):
        enumv.declare_anon(self._nextres)

    def handle( self, ctxt ):
        if not authentication.userid():
            return self.fail(ctxt)
        return self._nextres.handle(ctxt)

    def fail( self, ctxt ):
        """
        Called on authentication failure.
        """
        response.error(response.code.Forbidden)


class RequireAuthViaLogin(RequireAuth):
    """
    A handler which requires authentication to follow the request.
    """
    def __init__( self, redirect, nextres, **kwds ):
        RequireAuth.__init__(self, nextres, **kwds)
        self.redirect = redirect

    def fail( self, ctxt ):
        login_redirect(self.redirect, ctxt.locator.uri(), ctxt.args)


class PrivilegesBase(resource.Resource):
    """
    Class that initializes a set of privileges and a delegate resource.
    """
    def __init__( self, required_privileges, nextres, **kwds ):
        resource.Resource.__init__(self, **kwds)
        if isinstance(required_privileges, types.StringType):
            required_privileges = [required_privileges]
        self._required_privileges = required_privileges
        self._nextres = nextres
        assert isinstance(nextres, resource.Resource)

    def enum( self, enumv ):
        enumv.declare_anon(self._nextres)

class RequirePrivilege(PrivilegesBase):
    """
    A handler which requires any one of a list of privileges (OR) to follow the
    request.
    """
    def handle( self, ctxt ):
        if self._required_privileges:
            uid = authentication.userid()

            # You must be logged in to have any kind of privilege.
            if not uid:
                response.error(response.code.Forbidden)

            # Check each privilege in turn and break on the first one that
            # authorises (this is an OR logical).
            for p in self._required_privileges:
                if umprivileges.authorise(uid, p):
                    break
            else:
                response.error(response.code.Forbidden)

        return self._nextres.handle(ctxt)


class UserRoot(resource.WrapResource):
    """
    A handler that interprets the path component as a username and sets that
    user in the args for consumption by later handlers.
    """
    digitsre = re.compile('^\d+$')

    def __init__( self, next_resource, no_error=False, **kwds ):
        resource.WrapResource.__init__(self, next_resource, **kwds)
        self._no_error = no_error

    def enum( self, enumv ):
        enumv.declare_var('user', self.getnext())

    def handle_this( self, ctxt ):
        if ctxt.locator.isleaf():
            # no username specified
            response.error(response.code.NotFound)

        # allow those who can to access resources from obsolete users
        allowobs = umprivileges.authorise(authentication.userid(), 'obsolete')
        
        # accept either a userid (faster) or the username
        name = ctxt.locator.current()
        u = None
        if self.digitsre.match(name):
            try:
                u = umusers.getById(name, allowobs)
            except RuntimeError:
                if not self._no_error:
                    response.error(response.code.NotFound)
        else:
            # get user by username
            try:
                u = umusers.getByUser(name)
            except RuntimeError:
                if not self._no_error:
                    response.error(response.code.NotFound)

        # Add current user in arguments.
        ctxt.user = u

        # Consume path component in locator.
        ctxt.locator.next()


class UserChildren(PrivilegesBase):
    """
    Resource that serves the request as a public resource if it's a leaf, but
    whose children require the currently authenticated user to be the same as
    the user in the path (or to have certain privileges).  This is meant be used
    as a child under UserRoot (but not necessarily directly).
    """
    def handle( self, ctxt ):
        # if we're not a leaf (we leave the root as public)
        if not ctxt.locator.isleaf():
            # check the special privileges
            uid = authentication.userid()
            for p in self._required_privileges:
                if umprivileges.authorise(uid, p):
                    break
            else:
                # if no special privileges, require same user
                if ctxt.user.id != uid:
                    response.error(response.code.Forbidden)

        return self._nextres.handle(ctxt)


#-------------------------------------------------------------------------------
#
class LogRequestsWithUser(resource.WrapResource):

    fmt = '-----------[%05d] %s'
        
    def handle_this( self, ctxt ):
        logger.info(
            self.fmt % (authentication.userid() or 0, ctxt.locator.uri()))

