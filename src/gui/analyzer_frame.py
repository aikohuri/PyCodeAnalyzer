import os
from xml.dom import minidom
from multiprocessing import Process, Pipe, Queue
import datetime

import wx

from preprocessor import Preprocessor
from parser import Parser
from db_manager import DatabaseManager

import project_pane
import preprocessor_pane
import parser_pane
import execute_pane


class MainFrame(wx.Frame):

    def __init__(self, optionParser):
        style = wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL
        wx.Frame.__init__(self, None, -1, title=wx.EmptyString, size=wx.Size(817,696), style=style)

        self.projRootDir = ''
        self.analyzerOutDir = ''
        self.projInfo = {}
        self.dbname = ''

        self._initWigets()

        #
        # handle options
        #
        if optionParser.projFilePath:
            self._loadConfig(optionParser.projFilePath)
            self.exePane.multiprocessCb.SetValue(optionParser.multiprocessing)
            self.exePane.pipelineCb.SetValue(optionParser.pipeline)

            if optionParser.multiprocessing and optionParser.pipeline:
                self.exePane.numPpProcSc.SetValue(optionParser.numPpProc)
                self.exePane.numParserProcSc.SetValue(optionParser.numParserProc)
            elif optionParser.multiprocessing:
                self.exePane.numProcSc.SetValue(optionParser.numProc)

            if optionParser.execute:
                self.onExeBtn(None)

    def _initWigets(self):
        '''
        Initialize widgets
        '''
        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)
        self._createWidgets()
        self._layoutWidgets()
        self._connectEvents()

    def _createWidgets(self):
        '''
        Create widgets
        '''
        self._createMenuBar()
        self.notebook = wx.Notebook(self, -1, wx.DefaultPosition, wx.DefaultSize, 0)
        self.notebook.SetBackgroundColour((60,60,60))
        self.notebook.SetForegroundColour((230,230,230))
        self._createStartPage()

    def _createMenuBar(self):
        '''
        Create widgets in menubar
        '''
        self.m_menu1 = wx.Menu()

        self.menuItemOpen = wx.MenuItem(self.m_menu1, -1, u"Open\tCtrl+O", wx.EmptyString, wx.ITEM_NORMAL)
        self.menuItemSave = wx.MenuItem(self.m_menu1, -1, u"Save\tCtrl+S", wx.EmptyString, wx.ITEM_NORMAL)
        self.menuItemExit = wx.MenuItem(self.m_menu1, -1, u"Exit", wx.EmptyString, wx.ITEM_NORMAL)

        self.m_menu1.AppendItem(self.menuItemOpen)
        self.m_menu1.AppendItem(self.menuItemSave)
        self.m_menu1.AppendSeparator()
        self.m_menu1.AppendItem(self.menuItemExit)

        self.m_menubar1 = wx.MenuBar(0)
        self.m_menubar1.Append(self.m_menu1, u"File") 
        self.SetMenuBar(self.m_menubar1)

    def _createStartPage(self):
        '''
        Create widgets in start page
        '''
        self.startPage = wx.Panel(self.notebook, -1, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.startPage.SetBackgroundColour((60,60,60))
        self.startPage.SetForegroundColour((230,230,230))

        self.m_staticText1 = wx.StaticText(self.startPage, -1, u"Project Root Dir:", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_staticText1.Wrap(-1)

        self.projRootDirTc = wx.TextCtrl(self.startPage, -1, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_READONLY|wx.NO_BORDER)
        self.projRootDirBtn = wx.Button(self.startPage, -1, u"Browse", wx.DefaultPosition, wx.DefaultSize, 0)

        self.setupMenuLb = wx.Listbook(self.startPage, -1, wx.DefaultPosition, wx.DefaultSize, wx.LB_DEFAULT)
        self.setupMenuLb.SetBackgroundColour((60,60,60))
        self.setupMenuLb.SetForegroundColour((230,230,230))

        self.projPane = project_pane.ProjectPane(self.setupMenuLb, self)
        self.ppPane = preprocessor_pane.PpPane(self.setupMenuLb, self)
        self.parserPane = parser_pane.ParserPane(self.setupMenuLb, self)
        self.exePane = execute_pane.ExecutePane(self.setupMenuLb, self)

        self.setupMenuLb.AddPage(self.projPane   , u"Project Setup"      , True)
        self.setupMenuLb.AddPage(self.ppPane     , u"Preprocessor Setup" , False)
        self.setupMenuLb.AddPage(self.parserPane , u"Parser Setup"       , False)
        self.setupMenuLb.AddPage(self.exePane    , u"Execute"            , False)

        self.notebook.AddPage(self.startPage, u"Start", False)

    def _layoutWidgets(self):
        '''
        Layout widgets
        '''
        self._layoutStartPage()

        bSizer1 = wx.BoxSizer(wx.VERTICAL)
        bSizer1.Add(self.notebook, 1, wx.EXPAND |wx.ALL, 5)
        
        self.SetSizer(bSizer1)
        self.Layout()

    def _layoutStartPage(self):
        '''
        Layout widgets in start page
        '''
        bSizer2 = wx.BoxSizer(wx.VERTICAL)

        bSizer3 = wx.BoxSizer(wx.HORIZONTAL)
        bSizer3.Add(self.m_staticText1, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        bSizer3.Add(self.projRootDirTc, 1, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        bSizer3.Add(self.projRootDirBtn, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        bSizer2.Add(bSizer3, 0, wx.EXPAND, 5)
        bSizer2.Add(self.setupMenuLb, 1, wx.EXPAND |wx.ALL, 5)

        self.startPage.SetSizer(bSizer2)
        self.startPage.Layout()
        bSizer2.Fit(self.startPage)

    def _getAttr(self, attrName):
        return self.__dict__.get(attrName, None)

    def _connectEvents(self):
        '''
        Connect events to event handlers
        '''
        self.Bind(wx.EVT_MENU, self.onOpen, id=self.menuItemOpen.GetId())
        self.Bind(wx.EVT_MENU, self.onSave, id=self.menuItemSave.GetId())
        self.Bind(wx.EVT_MENU, self.onExit, id=self.menuItemExit.GetId())
        self.projRootDirBtn.Bind(wx.EVT_BUTTON, self.onProjRootDirBtn)

    def onOpen(self, evt):
        dlg = wx.FileDialog(self,
                            message="Choose File",
                            defaultDir=self.projRootDir if self.projRootDir else os.path.expanduser('~'),
                            defaultFile='',
                            wildcard="xml file|*.xml",
                            style=wx.FD_OPEN)
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self._loadConfig(path)

        dlg.Destroy()

    def _loadConfig(self, path):
        doc = minidom.parse(path)
        #
        # Load project directory
        #
        self.projRootDir = os.path.expanduser(doc.getElementsByTagName('project_setup')[0].attributes['dir'].value)
        self.projRootDirTc.SetValue(self.projRootDir)
        self.analyzerOutDir = os.path.join(self.projRootDir, 'analyzer_output')
        self.dbname = ''.join([self.projRootDir.replace(os.sep, '_').strip('_'), '.sqlite'])
        self.exePane.dbPathTc.SetValue(os.path.join(self.analyzerOutDir, self.dbname))
        self.exePane.ppLogFileTc.SetValue(os.path.join(self.analyzerOutDir, 'preprocessor.log'))
        self.exePane.parserLogFileTc.SetValue(os.path.join(self.analyzerOutDir, 'parser.log'))
        self.parserPane.outDirTc.SetValue(os.path.join(self.analyzerOutDir, 'parse_tree'))
        self.ppPane.outDirTc.SetValue(os.path.join(self.analyzerOutDir, 'pp'))

        self.projPane.setConfig(doc)
        self.ppPane.setConfig(doc)
        self.parserPane.setConfig(doc)

    def onSave(self, evt):
        dialog = wx.FileDialog(self,
                               message="Save File",
                               defaultDir=self.projRootDir if self.projRootDir else os.path.expanduser('~'),
                               defaultFile='proj_setting.xml',
                               style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        dialog.CenterOnParent()

        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self._saveConfig(path)

        dialog.Destroy()

    def _saveConfig(self, path):
        doc = minidom.Document()
        rootElem = doc.createElement('project')
        rootElem.appendChild(self.projPane.getConfig(doc))
        rootElem.appendChild(self.ppPane.getConfig(doc))
        rootElem.appendChild(self.parserPane.getConfig(doc))
        doc.appendChild(rootElem)

        fptr = open(path, 'w')
        fptr.write(doc.toprettyxml())
        fptr.close()

    def onExit(self, evt):
        self.Destroy()

    def onProjRootDirBtn(self, event):
        dlg = wx.DirDialog(self,
                           'Select project directory',
		                   self.projRootDir if self.projRootDir else os.path.expanduser('~'),
                           style=wx.DD_DEFAULT_STYLE
                           )
        dlg.CenterOnParent()

        if dlg.ShowModal() == wx.ID_OK:
            self.projRootDir = dlg.GetPath()
            self.projRootDirTc.SetValue(self.projRootDir)
            self.analyzerOutDir = os.path.join(self.projRootDir, 'analyzer_output')
            self.dbname = ''.join([self.projRootDir.replace(os.sep, '_').strip('_'), '.sqlite'])
            self.exePane.dbPathTc.SetValue(os.path.join(self.analyzerOutDir, self.dbname))
            self.exePane.ppLogFileTc.SetValue(os.path.join(self.analyzerOutDir, 'preprocessor.log'))
            self.exePane.parserLogFileTc.SetValue(os.path.join(self.analyzerOutDir, 'parser.log'))
            self.projPane.populateTree()
            self.ppPane.addIncludeDirs()

        dlg.Destroy()

    def getPpCfg(self):
        cfg = self.ppPane.getValue()
        cfg.update(self.exePane.getPpLogValue())
        return cfg

    def getParserCfg(self):
        cfg = self.parserPane.getValue()
        cfg.update(self.exePane.getParserLogValue())
        return cfg

    def onExeBtn(self, event):
        srcFiles = self.projPane.getValue()

        self.analyzerOutDir = os.path.join(self.projRootDir, 'analyzer_output')
        oldcwd = os.getcwd()

        if not os.path.exists(self.analyzerOutDir):
            os.makedirs(self.analyzerOutDir)

        os.chdir(self.analyzerOutDir)

        rcv_pipe, snd_pipe = Pipe(duplex=True)

        self.dbname = ''.join([self.projRootDir.replace(os.sep, '_').strip('_'), '.sqlite'])

        self.exePane.dbPathTc.SetValue(os.path.join(self.analyzerOutDir, self.dbname))
        self.exePane.ppLogFileTc.SetValue(os.path.join(self.analyzerOutDir, 'preprocessor.log'))
        self.exePane.parserLogFileTc.SetValue(os.path.join(self.analyzerOutDir, 'parser.log'))

        p = Process(target=analyze,
                    args=(snd_pipe,
                          os.path.join(self.analyzerOutDir, self.dbname),
                          self.getPpCfg(),
                          self.getParserCfg(),
                          srcFiles,
                          self.exePane.pipelineCb.GetValue(),
                          self.exePane.numProcSc.GetValue(),
                          self.exePane.numPpProcSc.GetValue(),
                          self.exePane.numParserProcSc.GetValue(),
                          ))
        p.start()
        dlg = wx.ProgressDialog('Executing',
                                     '0/%d' % len(srcFiles),
                                     parent=self,
                                     maximum=len(srcFiles)*10,
                                     style=wx.PD_CAN_ABORT |
                                           wx.PD_APP_MODAL |
                                           wx.PD_ELAPSED_TIME
                                     )
        dlg.SetSize((500,150))
        dlg.Layout()
        dlg.Show()

        result = None
        while True:
            i, total, result = rcv_pipe.recv()
            ret = dlg.Update(i*10, result if i == total else '[%d/%d] %s ... done' % (i+1, total, result))
            if ret[0] == False:
                rcv_pipe.send('STOP')
                while result != 'STOPPED':
                    result = rcv_pipe.recv()
                dlg.Update(total*10, 'Canceled')
                break
            if i == total:
                break
        p.join()

        self.exePane.dbPathTc.SetValue(os.path.join(self.analyzerOutDir, self.dbname))

        os.chdir(oldcwd)



def analyze(snd_pipe, db_path, pp_cfg, parser_cfg, srcFiles, use_pipeline=False, analyzer_process=1, pp_process=1, parser_process=1):
    db = DatabaseManager()
    pp_list = [Preprocessor(**pp_cfg) for i in range(pp_process if use_pipeline else analyzer_process)]
    parser_list = [Parser(**parser_cfg) for i in range(parser_process if use_pipeline else analyzer_process)]
    numFiles = len(srcFiles)
    use_pipeline = use_pipeline

    t_0 = datetime.datetime.now()

    projInfo = {}
    projInfo['predefined'] = pp_list[0].preprocess_predef()

    task_queue = Queue()
    done_queue = Queue()

    for i, srcFile in enumerate(srcFiles):
        task_queue.put(srcFile)
    for i in range(len(pp_list)):
        task_queue.put('STOP')

    if not use_pipeline:
        analyzer_p_list = [Process(target=analyzer_worker, args=(pp, parser, task_queue, done_queue)) for pp, parser in zip(pp_list, parser_list)]
        for analyzer_p in analyzer_p_list:
            analyzer_p.start()

        for i, srcFile in enumerate(srcFiles):
            #print 'analyze: [%d/%d]' % (i,numFiles), srcFile
            projInfo[srcFile] = done_queue.get()
            snd_pipe.send((i, numFiles, srcFile))
            if snd_pipe.poll():
                for analyzer_p in analyzer_p_list:
                    analyzer_p.terminate()
                for analyzer_p in analyzer_p_list:
                    analyzer_p.join()
                Preprocessor.clearTokenCache()
                snd_pipe.send('STOPPED')
                print 'analyze: canceled'
                return
        for analyzer_p in analyzer_p_list:
            analyzer_p.join()
    else:
        pp_queue = Queue()

        pp_p_list = [Process(target=preprocessor_worker, args=(pp, task_queue, pp_queue)) for pp in pp_list]
        for pp_p in pp_p_list:
            pp_p.start()

        parser_p_list = [Process(target=parser_worker, args=(parser, pp_queue, done_queue)) for parser in parser_list]
        for parser_p in parser_p_list:
            parser_p.start()

        for i, srcFile in enumerate(srcFiles):
            #print 'analyze: [%d/%d]' % (i,numFiles), srcFile
            projInfo[srcFile] = done_queue.get()
            snd_pipe.send((i, numFiles, srcFile))
            if snd_pipe.poll():
                for pp_p in pp_p_list:
                    pp_p.terminate()
                for parser_p in parser_p_list:
                    parser_p.terminate()
                for pp_p in pp_p_list:
                    pp_p.join()
                for parser_p in parser_p_list:
                    parser_p.join()
                Preprocessor.clearTokenCache()
                snd_pipe.send('STOPPED')
                print 'analyze: canceled'
                return

        for i in range(len(parser_p_list)):
            pp_queue.put('STOP')
        for pp_p in pp_p_list:
            pp_p.join()
        for parser_p in parser_p_list:
            parser_p.join()

    t_1 = datetime.datetime.now()

    db.createDB(db_path)
    db.addData(projInfo)
    db.saveDB()

    db.closeDB()

    print 'analyze: done', t_1 - t_0
    snd_pipe.send((numFiles, numFiles, 'Generating Database ... done'))

def analyzer_worker(pp, parser, input_queue, output_queue):
    t_0 = datetime.datetime.now()
    counter = 0
    for srcFile in iter(input_queue.get, 'STOP'):
        #print 'analyzer_worker:', srcFile, counter
        output_queue.put(parser.parse(pp.preprocess(srcFile)))
        counter += 1
    t_1 = datetime.datetime.now()
    print 'analyzer_worker: done', t_1 - t_0

def preprocessor_worker(pp, input_queue, output_queue):
    t_0 = datetime.datetime.now()
    counter = 0
    for srcFile in iter(input_queue.get, 'STOP'):
        #print 'preprocessor_worker:', srcFile, counter
        output_queue.put(pp.preprocess(srcFile))
        counter += 1
    t_1 = datetime.datetime.now()
    print 'preprocessor_worker: done', t_1 - t_0

def parser_worker(parser, input_queue, output_queue):
    t_0 = datetime.datetime.now()
    counter = 0
    for ppInfo in iter(input_queue.get, 'STOP'):
        #print 'parsre_worker:', ppInfo if ppInfo == 'STOP' else ppInfo['path'], counter
        output_queue.put(parser.parse(ppInfo))
        counter += 1
    t_1 = datetime.datetime.now()
    print 'parser_worker: done', t_1 - t_0

