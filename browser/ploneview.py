from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent
from Products.CMFCore.interfaces import IMembershipTool
from Products.CMFCore.interfaces import IPropertiesTool
from Products.CMFCore.permissions import AddPortalContent
from Products.CMFCore.permissions import DeleteObjects
from Products.CMFCore.permissions import ListFolderContents
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ReviewPortalContent
from Products.CMFCore.utils import _checkPermission
from Products.CMFPlone import utils
from Products.CMFPlone.browser.interfaces import IPlone
from Products.CMFPlone.interfaces import IBrowserDefault
from Products.CMFPlone.interfaces import INonStructuralFolder
from Products.CMFPlone.interfaces import IPloneTool
from Products.CMFPlone.interfaces.NonStructuralFolder import INonStructuralFolder\
     as z2INonStructuralFolder
from Products.CMFPlone.interfaces import ITranslationServiceTool

from zope.deprecation import deprecate, deprecated
from zope.interface import implements, alsoProvides
from zope.component import getMultiAdapter, queryMultiAdapter, getUtility

import ZTUtils
import sys

from plone.memoize.view import memoize
from plone.portlets.interfaces import IPortletManager, IPortletManagerRenderer

from plone.app.layout.globals.interfaces import IViewView
from plone.app.layout.icons.interfaces import IContentIcon

deprecated(
    ('IndexIterator'),
    "This reference to IndexIterator will be removed in Plone 3.5. Please "
    "import it from Products.CMFPlone.utils instead.")

IndexIterator = utils.IndexIterator

_marker = []

import zope.deferredimport
zope.deferredimport.deprecated(
    "It has been replaced by plone.memoize.instance.memoize. This alias will " 
    "be gone in Plone 3.5.",
    cache_decorator = 'plone.memoize.instance:memoize',
    )

class Plone(utils.BrowserView):
    implements(IPlone)

    def globalize(self):
        """
        Pure optimization hack, globalizes entire view for speed. Yes
        it's evil, but this hack will eventually be removed after
        globals are officially deprecated.

        YOU CAN ONLY CALL THIS METHOD FROM A PAGE TEMPLATE AND EVEN
        THEN IT MIGHT DESTROY YOU!
        """
        context = sys._getframe(2).f_locals['econtext']
        # Some of the original global_defines used 'options' to get parameters
        # passed in through the template call, so we need this to support
        # products which may have used this little hack
        options = context.vars.get('options',{})
        view = context.vars.get('view', None)
        template = context.vars.get('template', None)

        state = {}
        self._initializeData(options=options, view=view, template=template)
        for name, v in self._data.items():
            state[name] = v
            context.setGlobal(name, v)

    def __init__(self, context, request):
        super(Plone, self).__init__(context, request)
        self._data = {}

    def _initializeData(self, options=None, view=None, template=None):
        # We don't want to do this in __init__ because the view provides
        # methods which are useful outside of globals.  Also, performing
        # actions during __init__ is dangerous because instances are usually
        # created during traversal, which means authentication hasn't yet
        # happened.
        context = utils.context(self)
        if options is None:
            options = {}
        if view is None:
            view = self

        # XXX: Can't store data as attributes directly because it will
        # insert the view into the acquisition chain. Someone should
        # come up with a way to prevent this or get rid of the globals
        # view altogether

        tools = getMultiAdapter((context, self.request), name=u'plone_tools')
        portal_state = getMultiAdapter((context, self.request), name=u'plone_portal_state')
        context_state = getMultiAdapter((context, self.request), name=u'plone_context_state')

        self._data['utool'] = utool = tools.url()
        self._data['portal'] = portal = portal_state.portal()
        self._data['portal_url'] =  portal_state.portal_url()
        self._data['mtool'] = mtool = tools.membership()
        self._data['atool'] = atool = tools.actions()
        self._data['putils'] = putils = getUtility(IPloneTool)
        self._data['acl_users'] = getattr(portal, 'acl_users')
        self._data['wtool'] = wtool = tools.workflow()
        self._data['ifacetool'] = tools.interface()
        self._data['syntool'] = tools.syndication()
        self._data['portal_title'] = portal_state.portal_title()
        self._data['object_title'] = context_state.object_title()
        self._data['checkPermission'] = checkPermission = mtool.checkPermission
        self._data['member'] = portal_state.member()
        self._data['membersfolder'] =  mtool.getMembersFolder()
        self._data['isAnon'] =  portal_state.anonymous()
        self._data['actions'] = actions = (options.get('actions', None) or context_state.actions())
        self._data['keyed_actions'] =  context_state.keyed_actions()
        self._data['user_actions'] =  actions['user']
        self._data['workflow_actions'] =  actions['workflow']
        self._data['folder_actions'] =  actions['folder']
        self._data['global_actions'] =  actions['global']

        portal_tabs_view = getMultiAdapter((context, context.REQUEST), name='portal_tabs_view')
        self._data['portal_tabs'] =  portal_tabs_view.topLevelTabs(actions=actions)

        self._data['wf_state'] =  context_state.workflow_state()
        self._data['portal_properties'] = props = tools.properties()
        self._data['site_properties'] = site_props = props.site_properties
        self._data['ztu'] =  ZTUtils
        self._data['isFolderish'] =  context_state.is_folderish()
        
        self._data['sl'] = have_left_portlets = self.have_portlets('plone.leftcolumn', view)
        self._data['sr'] = have_right_portlets = self.have_portlets('plone.rightcolumn', view)
        self._data['hidecolumns'] =  self.hide_columns(have_left_portlets, have_right_portlets)
        
        self._data['here_url'] =  context_state.object_url()
        self._data['default_language'] = portal_state.default_language()
        self._data['language'] =  portal_state.language()
        self._data['is_editable'] = context_state.is_editable()
        self._data['isLocked'] = context_state.is_locked()
        self._data['isRTL'] =  portal_state.is_rtl()
        self._data['visible_ids'] =  self.visibleIdsEnabled() or None
        self._data['current_page_url'] =  context_state.current_page_url()
        self._data['normalizeString'] = putils.normalizeString
        self._data['toLocalizedTime'] = self.toLocalizedTime
        self._data['isStructuralFolder'] = context_state.is_structural_folder()
        self._data['isContextDefaultPage'] = context_state.is_default_page()

        self._data['navigation_root_url'] = portal_state.navigation_root_url()
        self._data['Iterator'] = utils.IndexIterator
        self._data['tabindex'] = utils.IndexIterator(pos=30000, mainSlot=False)
        self._data['uniqueItemIndex'] = utils.RealIndexIterator(pos=0)

        template_id = options.get('template_id', None)
        if template_id is None and template is not None:
            template_id = template.getId()
        self._data['template_id'] = template_id
        
        isViewTemplate = context_state.is_view_template()
        if isViewTemplate and not IViewView.providedBy(view):
            # Mark the view as being "the" view
            alsoProvides(view, IViewView)
            
        self._data['isViewTemplate'] = isViewTemplate

    # XXX: This is lame
    def hide_columns(self, column_left, column_right):
        if not column_right and not column_left:
            return "visualColumnHideOneTwo"
        if column_right and not column_left:
            return "visualColumnHideOne"
        if not column_right and column_left:
            return "visualColumnHideTwo"
        return "visualColumnHideNone"

    # Utility methods
    
    def toLocalizedTime(self, time, long_format=None):
        """Convert time to localized time
        """
        context = utils.context(self)
        util = getUtility(ITranslationServiceTool)
        return util.ulocalized_time(time, long_format, context,
                                    domain='plonelocales')
    
    @memoize
    def visibleIdsEnabled(self):
        """Determine if visible ids are enabled
        """
        context = utils.context(self)
        props = getUtility(IPropertiesTool).site_properties
        if not props.getProperty('visible_ids', False):
            return False

        pm=context.portal_membership
        if pm.isAnonymousUser():
            return False

        user = pm.getAuthenticatedMember()
        if user is not None:
            return user.getProperty('visible_ids', False)
        return False
    
    @memoize
    def displayContentsTab(self):
        """Whether or not the contents tabs should be displayed
        """
        context = utils.context(self)
        modification_permissions = (ModifyPortalContent,
                                    AddPortalContent,
                                    DeleteObjects,
                                    ReviewPortalContent)

        contents_object = context
        # If this object is the parent folder's default page, then the
        # folder_contents action is for the parent, we check permissions
        # there. Otherwise, if the object is not folderish, we don not display
        # the tab.
        if self.isDefaultPageInFolder():
            contents_object = self.getCurrentFolder()
        elif not self.isStructuralFolder():
            return 0

        # If this is not a structural folder, stop.
        plone_view = getMultiAdapter((contents_object, self.request),
                                     name='plone')
        if not plone_view.isStructuralFolder():
            return 0

        show = 0
        # We only want to show the 'contents' action under the following
        # conditions:
        # - If you have permission to list the contents of the relavant
        #   object, and you can DO SOMETHING in a folder_contents view. i.e.
        #   Copy or Move, or Modify portal content, Add portal content,
        #   or Delete objects.

        # Require 'List folder contents' on the current object
        if _checkPermission(ListFolderContents, contents_object):
            # If any modifications are allowed on object show the tab.
            for permission in modification_permissions:
                if _checkPermission(permission, contents_object):
                    show = 1
                    break

        return show

    @memoize
    def icons_visible(self):
        membership = getUtility(IMembershipTool)
        properties = getUtility(IPropertiesTool)

        site_properties = getattr(properties, 'site_properties')
        icon_visibility = site_properties.getProperty('icon_visibility', 'enabled')

        if icon_visibility == 'enabled':
            return True
        elif icon_visibility == 'authenticated' and not membership.isAnonymousUser():
            return True
        else:
            return False

    def getIcon(self, item):
        """Returns an object which implements the IContentIcon interface and
           provides the informations necessary to render an icon.
           The item parameter needs to be adaptable to IContentIcon.
           Icons can be disabled globally or just for anonymous users with
           the icon_visibility property in site_properties."""
        context = utils.context(self)
        if not self.icons_visible():
            icon = getMultiAdapter((context, self.request, None), IContentIcon)
        else:
            icon = getMultiAdapter((context, self.request, item), IContentIcon)
        return icon

    def normalizeString(self, text, relaxed=False):
        """Normalizes a title to an id.
        """
        return utils.normalizeString(text, context=self, relaxed=relaxed)

    def cropText(self, text, length, ellipsis='...'):
        """Crop text on a word boundary
        """
        converted = False
        if not isinstance(text, unicode):
            encoding = utils.getSiteEncoding(utils.context(self))
            text = unicode(text, encoding)
            converted = True
        if len(text)>length:
            text = text[:length]
            l = text.rfind(' ')
            if l > length/2:
                text = text[:l+1]
            text += ellipsis
        if converted:
            # encode back from unicode
            text = text.encode(encoding)
        return text

    # Deprecated in favour of the @@plone_context_state and @@plone_portal_state views

    @deprecate("The keyFilteredActions method of the Plone view has been "
               "deprecated and will be removed in Plone 3.5. Use the "
               "keyed_actions method of the plone_context_state adapter "
               "instead.")
    def keyFilteredActions(self, actions=None):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.keyed_actions()

    # @deprecate("The getCurrentUrl method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "current_page_url method of the plone_context_state adapter "
    #            "instead.")
    def getCurrentUrl(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.current_page_url()

    @deprecate("The isRightToLeft method of the Plone view has been "
               "deprecated and will be removed in Plone 3.5. Use the "
               "is_rtl method of the plone_portal_state adapter instead.")
    def isRightToLeft(self, domain='plone'):
        portal_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_portal_state')
        return portal_state.is_rtl()

    # @deprecate("The isDefaultPageInFolder method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "is_default_page method of the plone_context_state adapter "
    #            "instead.")
    def isDefaultPageInFolder(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.is_default_page()

    # @deprecate("The isStructuralFolder method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "is_structural_folder method of the plone_context_state adapter "
    #            "instead.")
    def isStructuralFolder(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.is_structural_folder()

    # @deprecate("The navigationRootPath method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "navigation_root_path method of the plone_portal_state adapter "
    #            "instead.")
    def navigationRootPath(self):
        portal_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_portal_state')
        return portal_state.navigation_root_path()

    # @deprecate("The navigationRootUrl method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "navigation_root_url method of the plone_portal_state adapter "
    #            "instead.")
    def navigationRootUrl(self):
        portal_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_portal_state')
        return portal_state.navigation_root_url()

    # @deprecate("The getParentObject method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "parent method of the plone_context_state adapter instead.")
    def getParentObject(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.parent()

    # @deprecate("The getCurrentFolder method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "folder method of the plone_context_state adapter instead.")
    def getCurrentFolder(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.folder()

    # @deprecate("The getCurrentFolderUrl method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "absolute_url method on the result of the folder method of the "
    #            "plone_context_state adapter instead.")
    def getCurrentFolderUrl(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.folder().absolute_url()

    # @deprecate("The getCurrentObjectUrl method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "canonical_object_url method of the plone_context_state "
    #            "adapter instead.")
    @memoize
    def getCurrentObjectUrl(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.canonical_object_url()

    # @deprecate("The isFolderOrFolderDefaultPage method of the Plone view has "
    #            "been deprecated and will be removed in Plone 3.5. Use either "
    #            "the is_structural_folder or is_default_page method of the "
    #            "plone_context_state adapter instead.")
    @memoize
    def isFolderOrFolderDefaultPage(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.is_structural_folder() or context_state.is_default_page()

    # @deprecate("The isPortalOrPortalDefaultPage method of the Plone view has "
    #            "been deprecated and will be removed in Plone 3.5. Use the "
    #            "is_portal_root method of the plone_context_state adapter "
    #            "instead.")
    @memoize
    def isPortalOrPortalDefaultPage(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.is_portal_root()
        
    # @deprecate("The getViewTemplateId method of the Plone view has been "
    #            "deprecated and will be removed in Plone 3.5. Use the "
    #            "view_template_id method of the plone_context_state adapter "
    #            "instead.")
    @memoize
    def getViewTemplateId(self):
        context_state = getMultiAdapter((utils.context(self), self.request), name=u'plone_context_state')
        return context_state.view_template_id()

    # Helper methods
    def have_portlets(self, manager_name, view=None):
        """Determine whether a column should be shown.
        The left column is called plone.leftcolumn; the right column is called
        plone.rightcolumn. Custom skins may have more portlet managers defined
        (see portlets.xml).
        """
        
        context = utils.context(self)
        if view is None:
            view = self

        manager = getUtility(IPortletManager, name=manager_name)
        renderer = queryMultiAdapter((context, self.request, view, manager), IPortletManagerRenderer)
        if renderer is None:
            renderer = getMultiAdapter((context, self.request, self, manager), IPortletManagerRenderer)

        return renderer.visible
