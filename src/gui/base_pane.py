import wx
import wx.lib.scrolledpanel as wxscrollpanel


class BasePane(wxscrollpanel.ScrolledPanel):

    def __init__(self, parent):
        style = wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER|wx.EXPAND
        wxscrollpanel.ScrolledPanel.__init__(self, parent, -1, style=style)

        self._initWigets()

    def _initWigets(self):
        '''
        Initialize widgets
        '''
        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)
        self._createWidgets()
        self._layoutWidgets()
        self._bindEvents()
        self.SetupScrolling()

    def _createWidgets(self):
        '''
        Create widgets
        '''
        raise NotImplementedError('Should have implemented this')

    def _layoutWidgets(self):
        '''
        Layout widgets
        '''
        raise NotImplementedError('Should have implemented this')

    def _bindEvents(self):
        '''
        Bind handlers to events
        '''
        raise NotImplementedError('Should have implemented this')

