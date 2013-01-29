import wx

from parser import Parser
import base_pane


class ParserPane(base_pane.BasePane):
    '''
    Parser setup pane
    '''

    def __init__(self, parent, root):
        self.root = root
        base_pane.BasePane.__init__(self, parent)

    def _createWidgets(self):
        self.SetBackgroundColour((60,60,60))
        self.SetForegroundColour((230,230,230))

        self._createBuiltinTypeWidgets()
        self._createSaveOptionWidgets()

    def _createBuiltinTypeWidgets(self):
        builtinTypes = Parser.getBuiltinTypes()
        self.builtinTypeLb = wx.ListBox(self, -1, wx.DefaultPosition, wx.DefaultSize, list(builtinTypes), 0)
        self.builtinTypeLb.SetBackgroundColour((30,30,30))
        self.builtinTypeLb.SetForegroundColour((230,230,230))

        self.builtinTypeAddBtn  = wx.Button(self, -1, u"Add")
        self.builtinTypeEditBtn = wx.Button(self, -1, u"Edit")
        self.builtinTypeDelBtn  = wx.Button(self, -1, u"Delete")

    def _createSaveOptionWidgets(self):
        self.saveCb = wx.CheckBox(self, -1, u"Save parse tree")
        self.saveCb.SetBackgroundColour((100,100,100))

        self.savePanel = wx.Panel(self, -1, style=wx.TAB_TRAVERSAL)
        self.savePanel.Show(False)
        self.savePanel.SetBackgroundColour((60,60,60))
        self.savePanel.SetForegroundColour((230,230,230))

        self.outDirTc = wx.TextCtrl(self.savePanel, -1, style=wx.TE_READONLY|wx.NO_BORDER)

    def _layoutWidgets(self):
        self._layoutSaveOptionWidgets()

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.AddSpacer((0, 5), 0, wx.EXPAND, 5)
        mainSizer.Add(self._layoutBuiltinTypeWidgets(), 1, wx.EXPAND, 5)
        mainSizer.Add(self.saveCb, 0, wx.ALL, 1)
        mainSizer.Add(self.savePanel, 0, wx.EXPAND |wx.ALL, 0)

        self.SetSizer(mainSizer)
        self.Layout()
        mainSizer.Fit(self)

    def _layoutBuiltinTypeWidgets(self):
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        btnSizer.Add(self.builtinTypeAddBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.builtinTypeEditBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.builtinTypeDelBtn, 0, wx.ALL|wx.SHAPED, 1)

        bSizer = wx.BoxSizer(wx.HORIZONTAL)
        bSizer.Add(self.builtinTypeLb, 1, wx.ALL|wx.EXPAND, 5)
        bSizer.Add(btnSizer, 0, wx.EXPAND, 5)

        sbSizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u" Built-in Types "), wx.VERTICAL)
        sbSizer.Add(bSizer, 1, wx.EXPAND, 5)
        return sbSizer

    def _layoutSaveOptionWidgets(self):
        outDirSizer = wx.BoxSizer(wx.HORIZONTAL)
        outDirSizer.Add(wx.StaticText(self.savePanel, -1, u"Output Dir:"), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        outDirSizer.Add(self.outDirTc, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        
        fgSizer = wx.FlexGridSizer(5, 2, 0, 0)
        fgSizer.AddGrowableCol(1)
        fgSizer.SetFlexibleDirection(wx.BOTH)
        fgSizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)
        fgSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        fgSizer.Add(outDirSizer, 1, wx.EXPAND, 5)
        
        self.savePanel.SetSizer(fgSizer)
        self.savePanel.Layout()
        fgSizer.Fit(self.savePanel)

    def _bindEvents(self):
        self.builtinTypeAddBtn.Bind(wx.EVT_BUTTON,  self.onBuiltinTypeAddBtn)
        self.builtinTypeEditBtn.Bind(wx.EVT_BUTTON, self.onBuiltinTypeEditBtn)
        self.builtinTypeDelBtn.Bind(wx.EVT_BUTTON,  self.onBuiltinTypeDelBtn)
        self.saveCb.Bind(wx.EVT_CHECKBOX, self.onSaveCb)

    def onBuiltinTypeAddBtn(self, evt):
        dlg = wx.TextEntryDialog(self, 'Type built-in type name:')
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            self.builtinTypeLb.Append(dlg.GetValue().strip())
            self.builtinTypeLb.Select(self.builtinTypeLb.GetCount()-1)
            self.builtinTypeLb.SetFocus()

        dlg.Destroy()

    def onBuiltinTypeEditBtn(self, evt):
        idx = self.builtinTypeLb.GetSelection()
        if idx < 0:
            return
        dlg = wx.TextEntryDialog(self, 'Type built-in type name:')
        dlg.CenterOnParent()
        dlg.SetValue(self.builtinTypeLb.GetString(idx))

        if dlg.ShowModal() == wx.ID_OK:
            self.builtinTypeLb.Append(dlg.GetValue().strip())
            self.builtinTypeLb.Select(self.builtinTypeLb.GetCount()-1)
            self.builtinTypeLb.SetFocus()

        dlg.Destroy()

    def onBuiltinTypeDelBtn(self, evt):
        idx = self.builtinTypeLb.GetSelection()
        if idx < 0:
            return
        self.builtinTypeLb.Delete(idx)
        if idx - 1 >= 0:
            self.builtinTypeLb.Select(idx-1)
        elif 0 <= idx < self.builtinTypeLb.GetCount():
            self.builtinTypeLb.Select(idx)
        self.builtinTypeLb.SetFocus()

    def onSaveCb(self, evt):
        self.savePanel.Show(evt.IsChecked())
        self.Layout()
        self.SetupScrolling()

    def setConfig(self, doc):
        parserElem = doc.getElementsByTagName('parser_setup')[0]
        self.saveCb.SetValue(eval(parserElem.attributes['save'].value))
        self.savePanel.Show(self.saveCb.GetValue())

        #
        # Load built-in types
        #
        self.builtinTypeLb.Clear()
        elem = parserElem.getElementsByTagName('builtin_types')[0]
        for node in elem.getElementsByTagName('type'):
            self.builtinTypeLb.Append(node.attributes['name'].value)

    def getConfig(self, doc):
        parserElem = doc.createElement('parser_setup')
        parserElem.setAttribute('save', str(self.saveCb.GetValue()))

        #
        # Save built-in types
        #
        elem = doc.createElement('builtin_types')
        for type in self.builtinTypeLb.GetItems():
            e = doc.createElement('type')
            e.setAttribute('name', type)
            elem.appendChild(e)
        parserElem.appendChild(elem)

        return parserElem

    def getValue(self):
        return {'builtinTypes': self.builtinTypeLb.GetItems(),
                'outDir': None if not self.saveCb.GetValue() else \
                          self.outDirTc.GetValue(),
                }

