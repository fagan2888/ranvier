#!/usr/bin/env python
# This file is part of the Ranvier package.
# See http://furius.ca/ranvier/ for license and details.

"""
Pretty printing the mapper contents.
"""

# stdlib imports
import StringIO

# ranvier imports
from ranvier.miscres import LeafResource


#-------------------------------------------------------------------------------
#
class PrettyEnumResource(LeafResource):
    """
    Output a rather nice page that describes all the pages that are being served
    from the given mapper.
    """
    def __init__( self, mapper, sorturls=False, **kwds ):
        """
        If 'sorturls' is True, we sort by URLs and change the rendering
        somewhat.
        """
        LeafResource.__init__(self, **kwds)
        self.mapper = mapper
        self.sorturls = sorturls

    def handle( self, ctxt ):
        ctxt.response.setContentType('text/html')
        self.render_header(ctxt.response)
        ctxt.response.write(pretty_render_mapper_body(self.mapper,
                                                      dict(ctxt.args),
                                                      self.sorturls))
        self.render_footer(ctxt.response)

    def render_header( self, oss ):
        """
        Output an HTML representation of the contents of the mapper (a str).

        This representation is meant to serve to the user for debugging, and
        includes the docstrings of the resource classes, if present.
        """
        oss.write('''
<html>
  <head>
    <title>URL Mapper Resources</title>
    <meta name="generator" content="Ranvier Pretty Resource Renderer" />
    <style type="text/css"><!--
body { font-size: smaller }
.resource-title { white-space: nowrap; }
p.docstring { margin-left: 2em; }
--></style>
 <body>
    ''')


    def render_footer( self, oss ):
        oss.write('''
 </body>
</html>
    ''')


#-------------------------------------------------------------------------------
#
def pretty_render_mapper_body( mapper, defaults, sorturls ):
    """
    Pretty-render just the body for the page that describes the contents of the
    mapper.
    """
    # Try to convert the defaults to ints if some are, this won't hurt.
    for name, value in defaults.iteritems():
        try:
            value = int(value)
            defaults[name] = value
        except ValueError:
            pass
    
    oss = StringIO.StringIO()
    oss.write('<h1>URL Mapper Resources</h1>\n')
    mappings = list(mapper.itervalues())
    if sorturls:
        sortkey = lambda x: x.urltmpl
        titfmt = ('<h2 class="resource-title"><tt>%(url)s</tt> '
                  '(<tt>%(resid)s</tt>)</h2>')
    else:
        sortkey = lambda x: x.resid
        titfmt = '<h2 class="resource-title"><tt>%(resid)s: %(url)s</tt></h2>'
    mappings.sort(key=sortkey)

    for o in mappings:
        # Prettify the URL somewhat for user readability.
        url = mapper.mapurl_pattern(o.resid)

        # Try to fill in missing values from in the defaults dict
        defdict = o.defdict.copy()
        for cname, cvalue in defaults.iteritems():
            if cname in defdict:
                defdict[cname] = cvalue
        
        # Make the URL clickable if it contains no parameters.
        if None not in defdict.itervalues():
            url = '<a href="%s">%s</a>' % (mapper.mapurl(o.resid, defdict), url)

        m = {'resid': o.resid,
             'url': url}

        oss.write(titfmt % m)
        if o.resource and o.resource.__doc__:
            oss.write('  <p class="docstring">%s</p>' % o.resource.__doc__)
    return oss.getvalue()

