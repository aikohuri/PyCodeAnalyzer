import os

import wx
import wx.lib.customtreectrl as wxcustomtreectrl

import base_pane


class ProjectPane(base_pane.BasePane):

    def __init__(self, parent, root):
        self.root = root
        self.srcFileItems = {}
        self.srcFileSet = set()

        base_pane.BasePane.__init__(self, parent)

    def _createWidgets(self):
        self.SetBackgroundColour((60,60,60))
        self.SetForegroundColour((230,230,230))

        style = wxcustomtreectrl.TR_DEFAULT_STYLE | \
                wxcustomtreectrl.TR_AUTO_CHECK_CHILD | \
                wxcustomtreectrl.TR_AUTO_CHECK_PARENT | \
                wxcustomtreectrl.TR_AUTO_TOGGLE_CHILD | \
                wxcustomtreectrl.TR_HAS_BUTTONS #|wxcustomtreectrl.TR_TWIST_BUTTONS
        #style&=~(wxcustomtreectrl.TR_NO_LINES)

        self.srcTreeCtrl = wxcustomtreectrl.CustomTreeCtrl(self, -1, agwStyle=style)
        self.srcTreeCtrl.SetBackgroundColour((30,30,30))
        self.srcTreeCtrl.SetForegroundColour((230,230,230))

    def _layoutWidgets(self):
        sbSizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, u"Source Files"), wx.VERTICAL)
        sbSizer.Add(self.srcTreeCtrl, 1, wx.EXPAND, 5)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(sbSizer, 1, wx.EXPAND, 5)
        
        self.SetSizer(mainSizer)
        self.Layout()
        mainSizer.Fit(self)

    def _bindEvents(self):
        pass

    def setConfig(self, doc):
        self.srcFileItems.clear()

        #
        # Load project source files
        #
        self.srcFileSet.clear()
        for node in doc.getElementsByTagName('srcFiles')[0].getElementsByTagName('path'):
            fname = node.attributes['value'].value.replace('{PROJ_ROOT}', self.root.projRootDir)
            if fname:
                self.srcFileSet.add(fname)

        self.populateTree()
        self.Layout()

    def getConfig(self, doc):
        projElem = doc.createElement('project_setup')
        projElem.setAttribute('dir', self.root.projRootDirTc.GetValue().replace(os.environ['HOME'], '~'))

        #
        # Save project source files
        #
        elem = doc.createElement('srcFiles')
        for f, cb in sorted(self.srcFileItems.items(), key=lambda v: v[0]):
            if cb.IsChecked():
                e = doc.createElement('path')
                e.setAttribute('value', f.replace(self.root.projRootDir, '{PROJ_ROOT}'))
                elem.appendChild(e)
        projElem.appendChild(elem)

        return projElem

    def populateTree(self):
        '''
        Construct source file tree
        '''
        self.srcTreeCtrl .DeleteAllItems()

        ids = {self.root.projRootDir: self.srcTreeCtrl.AddRoot(os.path.split(self.root.projRootDir)[-1], ct_type=1)}
        root = ids[self.root.projRootDir]
        self.srcTreeCtrl.SetItemBold(root, True)
        self.srcTreeCtrl.SetItemTextColour(root, (100,200,230))

        for dirpath, dirnames, filenames in os.walk(self.root.projRootDir):
            if '.svn' in dirpath or '.git' in dirpath:
                continue

            for dirname in sorted(dirnames):
                if '.svn' in dirname or '.git' in dirname:
                    continue

                fullpath = os.path.join(dirpath, dirname)
                item = self.srcTreeCtrl.AppendItem(ids[dirpath], dirname, ct_type=1) 
                ids[fullpath] = item
                self.srcTreeCtrl.SetItemBold(item, True)
                self.srcTreeCtrl.SetItemTextColour(item, (100,200,230))

            for filename in sorted([f for f in filenames if f.endswith('.c')]):
                item = self.srcTreeCtrl.AppendItem(ids[dirpath], filename, ct_type=1)
                path = os.path.join(dirpath, filename)
                item.SetData(path)
                self.srcFileItems[path] = item
                if path in self.srcFileSet:
                    self.srcFileSet.add(path)
                    self.srcTreeCtrl.CheckItem(self.srcFileItems[path], True)
                    parent = self.srcFileItems[path].GetParent()
                    while parent != root:
                        if not parent.IsExpanded():
                            self.srcTreeCtrl.Expand(parent)
                        parent = parent.GetParent()

        self.srcTreeCtrl.Expand(root)
        self.srcTreeCtrl.Refresh()

    def getValue(self):
        return sorted([path for path, item in self.srcFileItems.items() if item.IsChecked()])

