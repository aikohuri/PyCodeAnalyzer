import sys
import os

import wx

from preprocessor import Preprocessor
import base_pane


class PpPane(base_pane.BasePane):
    '''
    Preprocessor setup pane
    '''

    def __init__(self, parent, root):
        self.root = root
        base_pane.BasePane.__init__(self, parent)

    def _createWidgets(self):
        self.SetBackgroundColour((60,60,60))
        self.SetForegroundColour((230,230,230))

        self.processSysIncCb = wx.CheckBox(self, -1, u"Process #include <...> files")
        self.processSysIncCb.SetBackgroundColour((100,100,100))

        sysIncDirs, appIncDirs = Preprocessor.getDefaultIncDirs()
        self._createSysIncWidgets(sysIncDirs)
        self._createAppIncWidgets(appIncDirs)
        self._createPredefMacroWidgets()
        self._createSaveOptionWidgets()

    def _createSysIncWidgets(self, sysIncDirs):
        self.sysIncPanel = wx.Panel(self, -1, style=wx.TAB_TRAVERSAL)
        self.sysIncPanel.Show(False)
        self.sysIncPanel.SetBackgroundColour((60,60,60))
        self.sysIncPanel.SetForegroundColour((230,230,230))

        style=wx.LB_EXTENDED|wx.LB_HSCROLL|wx.LB_NEEDED_SB
        self.sysIncDirLb = wx.ListBox(self.sysIncPanel, -1, choices=sysIncDirs, style=style)
        self.sysIncDirLb.SetBackgroundColour((30,30,30))
        self.sysIncDirLb.SetForegroundColour((230,230,230))

        self.sysDirAddBtn  = wx.Button(self.sysIncPanel, -1, u"Add")
        self.sysDirEditBtn = wx.Button(self.sysIncPanel, -1, u"Edit")
        self.sysDirDelBtn  = wx.Button(self.sysIncPanel, -1, u"Delete")
        self.sysDirUpBtn   = wx.Button(self.sysIncPanel, -1, u"Up")
        self.sysDirDownBtn = wx.Button(self.sysIncPanel, -1, u"Down")

    def _createAppIncWidgets(self, appIncDirs):
        style=wx.LB_EXTENDED|wx.LB_HSCROLL|wx.LB_NEEDED_SB
        self.appIncDirLb = wx.ListBox(self, -1, choices=appIncDirs, style=style)
        self.appIncDirLb.SetBackgroundColour((30,30,30))
        self.appIncDirLb.SetForegroundColour((230,230,230))

        self.localDirAddBtn  = wx.Button(self, -1, u"Add")
        self.localDirEditBtn = wx.Button(self, -1, u"Edit")
        self.localDirDelBtn  = wx.Button(self, -1, u"Delete")
        self.localDirUpBtn   = wx.Button(self, -1, u"Up")
        self.localDirDownBtn = wx.Button(self, -1, u"Down")

    def _createPredefMacroWidgets(self):
        style = wx.LC_REPORT#|wx.LC_VRULES #|wx.LC_HRULES
        self.predefMacroLc = wx.ListCtrl(self, -1, style=style)
        self.predefMacroLc.InsertColumn(0, 'Name')
        self.predefMacroLc.InsertColumn(1, 'Value')
        self.predefMacroLc.SetBackgroundColour((30,30,30))
        self.predefMacroLc.SetForegroundColour((30,30,30))
        f = self.predefMacroLc.GetFont()
        f.SetFaceName("Monospace")
        self.predefMacroLc.SetFont(f)
        for name, val in sorted(Preprocessor.getPredefMacros().items(), key=lambda i: i[0]):
            idx = self.predefMacroLc.InsertStringItem(sys.maxint, name)
            self.predefMacroLc.SetStringItem(idx, 1, val)
            self.predefMacroLc.SetItemTextColour(idx, (255, 255, 255))

        self.predefAddBtn = wx.Button(self, -1, u"Add")
        self.predefEditBtn = wx.Button(self, -1, u"Edit")
        self.predefDelBtn = wx.Button(self, -1, u"Delete")

    def _createSaveOptionWidgets(self):
        self.saveCb = wx.CheckBox(self, -1, u"Save preprocessed files")
        self.saveCb.SetBackgroundColour((100,100,100))

        self.savePanel = wx.Panel(self, -1, style=wx.TAB_TRAVERSAL)
        self.savePanel.Show(False)
        self.savePanel.SetBackgroundColour((60,60,60))
        self.savePanel.SetForegroundColour((230,230,230))

        self.outDirTc = wx.TextCtrl(self.savePanel, -1, style=wx.TE_READONLY|wx.NO_BORDER)

        self.expandObjMacroCb = wx.CheckBox(self.savePanel, -1, u"Expand Object Macro")
        self.expandObjMacroCb.SetBackgroundColour((100,100,100))

        self.expandFuncMacroCb = wx.CheckBox(self.savePanel, -1, u"Expand Function Macro")
        self.expandFuncMacroCb.SetBackgroundColour((100,100,100))

        self.rmvCmtCb = wx.CheckBox(self.savePanel, -1, u"Remove Comments")
        self.rmvCmtCb.SetBackgroundColour((100,100,100))

        self.rmvAllPpCodeCb = wx.CheckBox(self.savePanel, -1, u"Remove All Preprocessor Directives")
        self.rmvAllPpCodeCb.SetBackgroundColour((100,100,100))

    def _layoutWidgets(self):
        self._layoutSysIncWidgets()
        self._layoutSaveOptionWidgets()
        
        bSizer = wx.BoxSizer(wx.VERTICAL)
        bSizer.AddSpacer((0, 5), 0, wx.EXPAND, 5)
        bSizer.Add(self.processSysIncCb, 0, wx.ALIGN_CENTER_VERTICAL, 5)
        bSizer.Add(self.sysIncPanel, 1, wx.EXPAND, 5)
        bSizer.AddSpacer((0, 5), 0, wx.EXPAND, 5)
        bSizer.Add(self._layoutAppIncWidgets(), 1, wx.EXPAND, 5)
        bSizer.AddSpacer((0, 5), 0, wx.EXPAND, 5)
        bSizer.Add(self._layoutPredefMacroWidgets(), 1, wx.EXPAND, 5)
        bSizer.AddSpacer((0, 5), 0, wx.EXPAND, 5)
        bSizer.Add(self.saveCb, 0, wx.ALL, 1)
        bSizer.Add(self.savePanel, 0, wx.EXPAND |wx.ALL, 0)

        self.SetSizer(bSizer)
        self.Layout()
        bSizer.Fit(self)

    def _layoutSysIncWidgets(self):
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        btnSizer.Add(self.sysDirAddBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.sysDirEditBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.sysDirDelBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.sysDirUpBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.sysDirDownBtn, 0, wx.ALL|wx.SHAPED, 1)

        bSizer = wx.BoxSizer(wx.HORIZONTAL)
        bSizer.Add(self.sysIncDirLb, 1, wx.ALL|wx.EXPAND, 5)
        bSizer.Add(btnSizer, 0, wx.EXPAND, 5)

        sbSizer = wx.StaticBoxSizer(wx.StaticBox(self.sysIncPanel, -1, u" #include <...> Search Dirs "), wx.VERTICAL)
        sbSizer.Add(bSizer, 1, wx.EXPAND, 5)

        self.sysIncPanel.SetSizer(sbSizer)
        self.sysIncPanel.Layout()
        sbSizer.Fit(self.sysIncPanel)

    def _layoutAppIncWidgets(self):
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        btnSizer.Add(self.localDirAddBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.localDirEditBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.localDirDelBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.localDirUpBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.localDirDownBtn, 0, wx.ALL|wx.SHAPED, 1)

        bSizer = wx.BoxSizer(wx.HORIZONTAL)
        bSizer.Add(self.appIncDirLb, 1, wx.ALL|wx.EXPAND, 5)
        bSizer.Add(btnSizer, 0, wx.EXPAND, 5)

        sbSizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u" #include \"...\" Search Dirs "), wx.VERTICAL)
        sbSizer.Add(bSizer, 1, wx.EXPAND, 5)
        return sbSizer

    def _layoutPredefMacroWidgets(self):
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        btnSizer.Add(self.predefAddBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.predefEditBtn, 0, wx.ALL|wx.SHAPED, 1)
        btnSizer.Add(self.predefDelBtn, 0, wx.ALL|wx.SHAPED, 1)
        
        bSizer = wx.BoxSizer(wx.HORIZONTAL)
        bSizer.Add(self.predefMacroLc, 1, wx.ALL|wx.EXPAND, 5)
        bSizer.Add(btnSizer, 0, wx.EXPAND, 5)
        
        sbSizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u" Predefine Macros "), wx.VERTICAL)
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
        fgSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        fgSizer.Add(self.expandObjMacroCb, 0, wx.ALL, 1)
        fgSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        fgSizer.Add(self.expandFuncMacroCb, 0, wx.ALL, 1)
        fgSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        fgSizer.Add(self.rmvCmtCb, 0, wx.ALL, 1)
        fgSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        fgSizer.Add(self.rmvAllPpCodeCb, 0, wx.ALL, 1)
        
        self.savePanel.SetSizer(fgSizer)
        self.savePanel.Layout()
        fgSizer.Fit(self.savePanel)

    def _bindEvents(self):
        self.processSysIncCb.Bind(wx.EVT_CHECKBOX, self.onProcessSysIncCb)
        self.sysDirAddBtn.Bind(wx.EVT_BUTTON, self.onSysDirAddBtn)
        self.sysDirEditBtn.Bind(wx.EVT_BUTTON, self.onSysDirEditBtn)
        self.sysDirDelBtn.Bind(wx.EVT_BUTTON, self.onSysDirDelBtn)
        self.sysDirUpBtn.Bind(wx.EVT_BUTTON, self.onSysDirUpBtn)
        self.sysDirDownBtn.Bind(wx.EVT_BUTTON, self.onSysDirDownBtn)
        self.localDirAddBtn.Bind(wx.EVT_BUTTON, self.onAppDirAddBtn)
        self.localDirEditBtn.Bind(wx.EVT_BUTTON, self.onAppDirEditBtn)
        self.localDirDelBtn.Bind(wx.EVT_BUTTON, self.onAppDirDelBtn)
        self.localDirUpBtn.Bind(wx.EVT_BUTTON, self.onAppDirUpBtn)
        self.localDirDownBtn.Bind(wx.EVT_BUTTON, self.onAppDirDownBtn)
        self.predefAddBtn.Bind(wx.EVT_BUTTON, self.onPredefAddBtn)
        self.predefEditBtn.Bind(wx.EVT_BUTTON, self.onPredefEditBtn)
        self.predefDelBtn.Bind(wx.EVT_BUTTON, self.onPredefDelBtn)
        self.saveCb.Bind(wx.EVT_CHECKBOX, self.onSavePpFileCb)

    def onProcessSysIncCb(self, evt):
        self.sysIncPanel.Show(evt.IsChecked())
        self.Layout()
        self.SetupScrolling()

    def onSysDirAddBtn(self, event):
        dlg = wx.DirDialog(self,
                           'Select search directory',
		                   self.root.projRootDir,
                           style=wx.DD_DEFAULT_STYLE
                           )
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            self.sysIncDirLb.Append(dlg.GetPath())
            self.sysIncDirLb.Select(self.sysIncDirLb.GetCount()-1)
            self.sysIncDirLb.SetFocus()

        dlg.Destroy()

    def onSysDirEditBtn(self, event):
        sels = self.sysIncDirLb.GetSelections()
        if not sels:
            return
        for idx in sels:
            dlg = wx.DirDialog(self,
                               'Select search directory',
                               self.sysIncDirLb.GetString(idx),
                               style=wx.DD_DEFAULT_STYLE
                               )
            dlg.CenterOnParent()

            if dlg.ShowModal() == wx.ID_OK:
                self.sysIncDirLb.SetString(idx, dlg.GetPath())
                self.sysIncDirLb.Select(idx)
                self.sysIncDirLb.SetFocus()

            dlg.Destroy()

    def onSysDirDelBtn(self, event):
        sels = self.sysIncDirLb.GetSelections()
        if not sels:
            return
        for idx in reversed(sels):
            self.sysIncDirLb.Delete(idx)
            if idx - 1 >= 0:
                self.sysIncDirLb.Select(idx-1)
            elif 0 <= idx < self.sysIncDirLb.GetCount():
                self.sysIncDirLb.Select(idx)
        self.sysIncDirLb.SetFocus()
    
    def onSysDirUpBtn(self, event):
        sels = self.sysIncDirLb.GetSelections()
        if not sels or sels[0] <= 0:
            return
        for idx in sels:
            lst = self.sysIncDirLb.GetItems()
            self.sysIncDirLb.SetString(idx-1, lst[idx])
            self.sysIncDirLb.SetString(idx, lst[idx-1])
            self.sysIncDirLb.Select(idx-1)
        self.sysIncDirLb.Deselect(sels[-1])
        self.sysIncDirLb.SetFocus()

    def onSysDirDownBtn(self, event):
        sels = self.sysIncDirLb.GetSelections()
        if not sels or sels[-1] >= self.sysIncDirLb.GetCount() - 1:
            return
        for idx in reversed(sels):
            lst = self.sysIncDirLb.GetItems()
            self.sysIncDirLb.SetString(idx, lst[idx+1])
            self.sysIncDirLb.SetString(idx+1, lst[idx])
            self.sysIncDirLb.Select(idx+1)
        self.sysIncDirLb.Deselect(sels[0])
        self.sysIncDirLb.SetFocus()
    
    def onAppDirAddBtn(self, event):
        dlg = wx.DirDialog(self,
                           'Select search directory',
		                   self.root.projRootDir,
                           style=wx.DD_DEFAULT_STYLE
                           )
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            self.appIncDirLb.Append(dlg.GetPath())
            self.appIncDirLb.Select(self.appIncDirLb.GetCount()-1)
            self.appIncDirLb.SetFocus()

        dlg.Destroy()
    
    def onAppDirEditBtn(self, event):
        sels = self.appIncDirLb.GetSelections()
        if not sels:
            return
        for idx in sels:
            dlg = wx.DirDialog(self,
                               'Select search directory',
                               self.appIncDirLb.GetString(idx),
                               style=wx.DD_DEFAULT_STYLE
                               )
            dlg.CenterOnParent()

            if dlg.ShowModal() == wx.ID_OK:
                self.appIncDirLb.SetString(idx, dlg.GetPath())
                self.appIncDirLb.Select(idx)
                self.appIncDirLb.SetFocus()

            dlg.Destroy()
    
    def onAppDirDelBtn(self, event):
        sels = self.appIncDirLb.GetSelections()
        if not sels:
            return
        for idx in reversed(sels):
            self.appIncDirLb.Delete(idx)
            if idx - 1 >= 0:
                self.appIncDirLb.Select(idx-1)
            elif 0 <= idx < self.appIncDirLb.GetCount():
                self.appIncDirLb.Select(idx)
        self.appIncDirLb.SetFocus()
    
    def onAppDirUpBtn(self, event):
        sels = self.appIncDirLb.GetSelections()
        if not sels or sels[0] <= 0:
            return
        for idx in sels:
            lst = self.appIncDirLb.GetItems()
            self.appIncDirLb.SetString(idx-1, lst[idx])
            self.appIncDirLb.SetString(idx, lst[idx-1])
            self.appIncDirLb.Select(idx-1)
        self.appIncDirLb.Deselect(sels[-1])
        self.appIncDirLb.SetFocus()
    
    def onAppDirDownBtn(self, event):
        sels = self.appIncDirLb.GetSelections()
        if not sels or sels[-1] >= self.appIncDirLb.GetCount() - 1:
            return
        for idx in reversed(sels):
            lst = self.appIncDirLb.GetItems()
            self.appIncDirLb.SetString(idx, lst[idx+1])
            self.appIncDirLb.SetString(idx+1, lst[idx])
            self.appIncDirLb.Select(idx+1)
        self.appIncDirLb.Deselect(sels[0])
        self.appIncDirLb.SetFocus()
    
    def onPredefAddBtn(self, event):
        dlg = PredefMacroDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            name, val = dlg.GetValue()
            idx = self.predefMacroLc.InsertStringItem(sys.maxint, name)
            self.predefMacroLc.SetStringItem(idx, 1, val)
            self.predefMacroLc.SetItemTextColour(idx, (255, 255, 255))
        dlg.Destroy()
        self.predefMacroLc.SetFocus()

    def onPredefEditBtn(self, event):
        row = self.predefMacroLc.GetFocusedItem()
        name = str(self.predefMacroLc.GetItem(row,0).GetText())
        value = str(self.predefMacroLc.GetItem(row,1).GetText())
        dlg = PredefMacroDialog(self, name, value)
        if dlg.ShowModal() == wx.ID_OK:
            name, val = dlg.GetValue()
            self.predefMacroLc.SetStringItem(row, 0, name)
            self.predefMacroLc.SetStringItem(row, 1, val)
        dlg.Destroy()
        self.predefMacroLc.SetFocus()

    def onPredefDelBtn(self, event):
        row = self.predefMacroLc.GetFocusedItem()
        if row < 0:
            return
        self.predefMacroLc.DeleteItem(row)
        self.predefMacroLc.SetFocus()
    
    def onSavePpFileCb(self, evt):
        self.savePanel.Show(evt.IsChecked())
        self.Layout()
        self.SetupScrolling()

    def setConfig(self, doc):
        ppElem = doc.getElementsByTagName('preprocessor_setup')[0]
        self.saveCb.SetValue(eval(ppElem.attributes['save'].value))
        self.expandObjMacroCb.SetValue(eval(ppElem.attributes['expandObj'].value))
        self.expandFuncMacroCb.SetValue(eval(ppElem.attributes['expandFunc'].value))
        self.rmvCmtCb.SetValue(eval(ppElem.attributes['rmvCmt'].value))
        self.savePanel.Show(self.saveCb.GetValue())

        self.sysIncDirLb.Clear()
        elem = ppElem.getElementsByTagName('sysIncDirs')[0]
        self.processSysIncCb.SetValue(eval(elem.attributes['process'].value))
        self.sysIncPanel.Show(self.processSysIncCb.GetValue())
        for node in elem.getElementsByTagName('dir'):
            self.sysIncDirLb.Append(node.attributes['value'].value)

        self.appIncDirLb.Clear()
        for node in ppElem.getElementsByTagName('localIncDirs')[0].getElementsByTagName('dir'):
            self.appIncDirLb.Append(os.path.expanduser(node.attributes['value'].value.replace('{PROJ_ROOT}',self.root.projRootDir)))

        self.predefMacroLc.ClearAll()
        self.predefMacroLc.InsertColumn(0, 'Name')
        self.predefMacroLc.InsertColumn(1, 'Value')
        for node in ppElem.getElementsByTagName('macro'):
            idx = self.predefMacroLc.InsertStringItem(sys.maxint, node.attributes['name'].value)
            self.predefMacroLc.SetStringItem(idx, 1, node.attributes['value'].value)
            self.predefMacroLc.SetItemTextColour(idx, (255, 255, 255))

    def getConfig(self, doc):
        ppElem = doc.createElement('preprocessor_setup')
        ppElem.setAttribute('save', str(self.saveCb.GetValue()))
        ppElem.setAttribute('expandObj', str(self.expandObjMacroCb.GetValue()))
        ppElem.setAttribute('expandFunc', str(self.expandFuncMacroCb.GetValue()))
        ppElem.setAttribute('rmvCmt', str(self.rmvCmtCb.GetValue()))

        #
        # Save system search directories
        #
        elem = doc.createElement('sysIncDirs')
        elem.setAttribute('process', str(self.processSysIncCb.GetValue()))
        for dir in self.sysIncDirLb.GetItems():
            e = doc.createElement('dir')
            e.setAttribute('value', dir)
            elem.appendChild(e)
        ppElem.appendChild(elem)

        #
        # Save local search directories
        #
        elem = doc.createElement('localIncDirs')
        for dir in self.appIncDirLb.GetItems():
            e = doc.createElement('dir')
            e.setAttribute('value', dir.replace(self.root.projRootDir,'{PROJ_ROOT}').replace(os.environ['HOME'],'~'))
            elem.appendChild(e)
        ppElem.appendChild(elem)

        #
        # Save predefined macros
        #
        elem = doc.createElement('predef_macros')
        for row in xrange(self.predefMacroLc.GetItemCount()):
            e = doc.createElement('macro')
            e.setAttribute('name', self.predefMacroLc.GetItem(row,0).GetText())
            e.setAttribute('value', self.predefMacroLc.GetItem(row,1).GetText())
            elem.appendChild(e)
        ppElem.appendChild(elem)

        return ppElem

    def getValue(self):
        predefMacros = dict([
            (str(self.predefMacroLc.GetItem(row,0).GetText()),
             str(self.predefMacroLc.GetItem(row,1).GetText())
             )
            for row in xrange(self.predefMacroLc.GetItemCount())
            ])

        return {'appIncDirs': self.appIncDirLb.GetItems(),
                'sysIncDirs': [] if not self.processSysIncCb.GetValue() else \
                              self.sysIncDirLb.GetItems(),
                'predefMacros': predefMacros,
                'save': self.saveCb.GetValue(),
                'removeComment': self.rmvCmtCb.GetValue(),
                'outputDir': self.outDirTc.GetValue(),
                'expandObjMacro': self.expandObjMacroCb.GetValue(),
                'expandFuncMacro': self.expandFuncMacroCb.GetValue(),
                }

    def addIncludeDirs(self):
        for curdir, dirs, files in os.walk(self.root.projRootDir):
            if '/pp/' in curdir or '.git' in curdir or '.svn' in curdir:
                continue
            if any([f.endswith('.h') for f in files]):
                self.appIncDirLb.Append(curdir)
        

class PredefMacroDialog(wx.Dialog):

    def __init__(self, parent, name='', value=''):
        wx.Dialog.__init__(self, parent, -1, title='Predefined Macro')

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(self, -1, 'Name:'), 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.nameTc = wx.TextCtrl(self, -1, name)
        hsizer.Add(self.nameTc, 1, wx.ALIGN_CENTER|wx.TOP|wx.LEFT|wx.RIGHT, 5)

        vsizer.Add(hsizer, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(self, -1, 'Value:'), 0, wx.ALIGN_CENTER|wx.ALL, 5)
        self.valueTc = wx.TextCtrl(self, -1, value)
        hsizer.Add(self.valueTc, 1, wx.ALIGN_CENTER|wx.ALL, 5)

        flag = wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.LEFT|wx.RIGHT
        vsizer.Add(hsizer, 0, flag=flag, border=5)

        flag = wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.LEFT|wx.RIGHT
        vsizer.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, flag=flag, border=5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        okBtn = wx.Button(self, wx.ID_OK, 'OK')
        hsizer.Add(okBtn, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        cancelBtn = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        hsizer.Add(cancelBtn, 0, wx.ALIGN_CENTER|wx.ALL, border=5)

        vsizer.Add(hsizer, 0, flag=flag, border=5)

        self.SetSizer(vsizer)
        vsizer.Fit(self)

        self.CenterOnParent()

    def GetValue(self):
        return self.nameTc.GetValue(), self.valueTc.GetValue()

