import wx
try:
    from agw import pycollapsiblepane as PCP
except:
    import wx.lib.agw.pycollapsiblepane as PCP

import base_pane


class ExecutePane(base_pane.BasePane):

    def __init__(self, parent, root):
        self.root = root
        base_pane.BasePane.__init__(self, parent)

    def _createWidgets(self):
        self.SetBackgroundColour((60,60,60))
        self.SetForegroundColour((230,230,230))

        self.ppLogLvlCb = wx.ComboBox(self, -1, size=(120,-1), choices=['DEBUG','INFO','WARNING','ERROR'])
        self.ppLogLvlCb.SetSelection(2)
        self.ppLogFileTc = wx.TextCtrl(self, -1, '', style=wx.TE_READONLY)

        self.parserLogLvlCb = wx.ComboBox(self, -1, size=(120,-1), choices=['DEBUG','INFO','WARNING','ERROR'])
        self.parserLogLvlCb.SetSelection(2)
        self.parserLogFileTc = wx.TextCtrl(self, -1, '', style=wx.TE_READONLY)

        self.multiprocessCb = wx.CheckBox(self, -1, 'Use multiprocessing')
        self.pipelineCb = wx.CheckBox(self, -1, 'Use pipeline')

        self.numProcSc = wx.SpinCtrl(self, -1, size=(60,23), min=1, max=100)
        self.numProcSc.SetForegroundColour('black')
        self.numProcSc.Disable()

        self.numPpProcSc = wx.SpinCtrl(self, -1, size=(60,23), min=1, max=100)
        self.numPpProcSc.SetForegroundColour('black')
        self.numPpProcSc.Disable()

        self.numParserProcSc = wx.SpinCtrl(self, -1, size=(60,23), min=1, max=100)
        self.numParserProcSc.SetForegroundColour('black')
        self.numParserProcSc.Disable()

        self.exeBtn = wx.Button(self, -1, u"Execute", wx.DefaultPosition, wx.DefaultSize, 0)

        self.dbPathTc = wx.TextCtrl(self, -1, '', style=wx.TE_READONLY)

    def _layoutWidgets(self):
        ppSizer = wx.BoxSizer(wx.HORIZONTAL)
        ppSizer.Add(wx.StaticText(self,-1,'Preprocessor Log Level:',size=(180,-1)), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        ppSizer.Add(self.ppLogLvlCb, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        ppSizer.Add(wx.StaticText(self,-1,'Log File Path:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        ppSizer.Add(self.ppLogFileTc, 1, wx.EXPAND|wx.ALL, 5)

        parserSizer = wx.BoxSizer(wx.HORIZONTAL)
        parserSizer.Add(wx.StaticText(self,-1,'Parser Log Level:',size=(180,-1)), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        parserSizer.Add(self.parserLogLvlCb, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        parserSizer.Add(wx.StaticText(self,-1,'Log File Path:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        parserSizer.Add(self.parserLogFileTc, 1, wx.EXPAND|wx.ALL, 5)

        multipSizer = wx.FlexGridSizer(3, 3, 0, 0)
        multipSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        multipSizer.Add(wx.StaticText(self,-1,'Num. of Processes:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        multipSizer.Add(self.numProcSc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        multipSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        multipSizer.Add(wx.StaticText(self,-1,'Num. of Preprocessor Processes:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        multipSizer.Add(self.numPpProcSc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        multipSizer.AddSpacer((30, 0), 1, wx.EXPAND, 5)
        multipSizer.Add(wx.StaticText(self,-1,'Num. of Parser Processes:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        multipSizer.Add(self.numParserProcSc, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        dbSizer = wx.BoxSizer(wx.HORIZONTAL)
        dbSizer.Add(wx.StaticText(self,-1,'Database Path:'), 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        dbSizer.Add(self.dbPathTc, 1, wx.EXPAND|wx.ALL, 5)

        bSizer = wx.BoxSizer(wx.VERTICAL)
        bSizer.Add(ppSizer, 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(parserSizer, 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(self.multiprocessCb, 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(self.pipelineCb, 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(multipSizer, 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(wx.StaticLine(self,-1,style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(dbSizer, 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(wx.StaticLine(self,-1,style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)
        bSizer.Add(self.exeBtn, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)

        self.SetSizer(bSizer)
        self.Layout()
        bSizer.Fit(self)

    def _bindEvents(self):
        self.exeBtn.Bind(wx.EVT_BUTTON, self.root.onExeBtn)
        self.pipelineCb.Bind(wx.EVT_CHECKBOX, self.onCheckBox)
        self.multiprocessCb.Bind(wx.EVT_CHECKBOX, self.onCheckBox)

    def onBrowseBtn(self, evt):
        obj = evt.GetEventObject()
        objName = obj.GetName()
        if eval('self.%sLogFileTc.GetValue()' % objName):
            exec 'd, f = os.path.split(self.%sLogFileTc.GetValue())' % objName
        else:
            d, f = self.root.analyzerOutDir, 'preprocessor.log' if objName == 'pp' else 'parser.log'
        dlg = wx.FileDialog(self,
                            defaultDir=d,
                            defaultFile=f,
                            style=wx.SAVE|wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            exec 'self.%sLogFileTc.SetValue(dlg.GetPath())' % objName
        dlg.Destroy()

    def onCheckBox(self, evt):
        pipeline = self.pipelineCb.GetValue()
        multiprocessing = self.multiprocessCb.GetValue()
        self.numProcSc.Enable(not pipeline and multiprocessing)
        self.numPpProcSc.Enable(pipeline and multiprocessing)
        self.numParserProcSc.Enable(pipeline and multiprocessing)
        if pipeline and multiprocessing:
            self.numProcSc.SetValue(1)
        else:
            self.numPpProcSc.SetValue(1)
            self.numParserProcSc.SetValue(1)

    def onPaneChanged(self, evt):
        self.Layout()
        if self.cp.IsExpanded():
            self.cp.SetLabel('Hide Log')
        else:
            self.cp.SetLabel('Show Log')

    def getPpLogValue(self):
        return {'logLevel': self.ppLogLvlCb.GetStringSelection(),
                'logPath' : self.ppLogFileTc.GetValue(),
                }

    def getParserLogValue(self):
        return {'logLevel': self.parserLogLvlCb.GetStringSelection(),
                'logPath' : self.parserLogFileTc.GetValue(),
                }

