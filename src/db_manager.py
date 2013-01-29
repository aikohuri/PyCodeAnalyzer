import sqlite3
import os
from collections import deque
import sha

from parser_types import *


class DatabaseManager:

    def __init__(self):
        self.conn = None
        self.cursor = None
        self.dbPath = ''

    def createDB(self, dbPath):
        self.dbPath = dbPath
        if os.path.exists(dbPath):
            os.remove(dbPath)

        if self.cursor:
            self.cursor.close()

        if self.conn:
            self.conn.close()

        self.conn = sqlite3.connect(dbPath)
        self.cursor = self.conn.cursor()

        self.createTable('File',
                         [('path'    , 'VARCHAR(512)', 'NOT NULL'),
                          ('size'    , 'INTEGER', 'NOT NULL'),
                          ('numLines', 'INTEGER', 'NOT NULL'),
                          ('isSrc'   , 'INTEGER', 'NOT NULL'),
                          ('SHA1'    , 'VARCHAR(20)', 'NOT NULL'),
                          ]
                         )

        self.createTable('Include',
                         [('path'       , 'VARCHAR(128)', 'NOT NULL'),
                          ('path_fid'   , 'INTEGER'),
                          ('root_fid'   , 'INTEGER', 'NOT NULL'),
                          ('depth'      , 'INTEGER', 'NOT NULL'),
                          ('fid'        , 'INTEGER', 'NOT NULL'),
                          ('row'        , 'INTEGER', 'NOT NULL'),
                          ('col'        , 'INTEGER', 'NOT NULL'),
                          #('PRIMARY KEY', '(root_fid, path_fid, fid, row, col)'),
                          ('FOREIGN KEY', '(path_fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY', '(root_fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY', '(fid)', 'REFERENCES File(rowid)'),
                          ]
                         )

        self.createTable('MacroDef',
                         [('name'          , 'VARCHAR(128)', 'NOT NULL'),
                          ('params'        , 'VARCHAR(256)'),
                          ('value'         , 'TEXT'),
                          ('expandedValue' , 'TEXT'),
                          ('fid'           , 'INTEGER', 'NOT NULL'),
                          ('row'           , 'INTEGER', 'NOT NULL'),
                          ('col'           , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY'   , '(name, fid, row, col)'),
                          ('FOREIGN KEY'   , '(fid)', 'REFERENCES File(rowid)'),
                          ]
                         )

        self.createTable('MacroUndef',
                         [('name'       , 'VARCHAR(128)', 'NOT NULL'),
                          ('fid'        , 'INTEGER', 'NOT NULL'),
                          ('row'        , 'INTEGER', 'NOT NULL'),
                          ('col'        , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY', '(fid, row, col)'),
                          ('FOREIGN KEY', '(fid)', 'REFERENCES File(rowid)'),
                         ]
                        )

        self.createTable('MacroUsage',
                         [('name'       , 'VARCHAR(128)', 'NOT NULL'),
                          ('fid'        , 'INTEGER', 'NOT NULL'),
                          ('row'        , 'INTEGER', 'NOT NULL'),
                          ('col'        , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY', '(fid, row, col)'),
                          ('FOREIGN KEY', '(fid)', 'REFERENCES File(rowid)'),
                         ]
                        )

        self.createTable('Pragma',
                         [('value'         , 'VARCHAR(256)'),
                          ('fid'           , 'INTEGER', 'NOT NULL'),
                          ('row'           , 'INTEGER', 'NOT NULL'),
                          ('col'           , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY'   , '(fid, row, col)'),
                          ('FOREIGN KEY'   , '(fid)', 'REFERENCES File(rowid)'),
                          ]
                         )

        self.createTable('DataType',
                         [('type'       , 'VARCHAR(8)', 'NOT NULL'),
                          ('name'       , 'VARCHAR(64)'),
                          ('hasFields'  , 'INTEGER', 'NOT NULL'),
                          ('fid'        , 'INTEGER', 'NOT NULL'),
                          ('row'        , 'INTEGER', 'NOT NULL'),
                          ('col'        , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY', '(fid, row, col)'),
                          ('FOREIGN KEY', '(fid)', 'REFERENCES File(rowid)'),
                          ]
                         )

        self.createTable('DataTypeField',
                         [('type'       , 'VARCHAR(128)'),
                          ('dataTypeId' , 'INTEGER'),
                          ('funcTypeId' , 'INTEGER'),
                          ('refType'    , 'VARCHAR(32)'),
                          ('name'       , 'VARCHAR(64)'),
                          ('dim'        , 'VARCHAR(32)'),
                          ('value'      , 'VARCHAR(32)'),
                          ('fid'        , 'INTEGER', 'NOT NULL'),
                          ('row'        , 'INTEGER', 'NOT NULL'),
                          ('col'        , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY', '(fid, row, col)'),
                          ('FOREIGN KEY', '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY', '(dataTypeId)', 'REFERENCES DataType(rowid)'),
                          ('FOREIGN KEY', '(funcTypeId)', 'REFERENCES Function(rowid)'),
                          ]
                         )

        self.createTable('DataTypeLink',
                         [('dataTypeId' , 'INTEGER', 'NOT NULL'),
                          ('fieldId'    , 'INTEGER', 'NOT NULL'),
                          ('depth'      , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY', '(dataTypeId, fieldId)'),
                          ('FOREIGN KEY', '(dataTypeId)', 'REFERENCES DataType(rowid)'),
                          ('FOREIGN KEY', '(fieldId)', 'REFERENCES DataTypeField(rowid)'),
                          ]
                         )

        self.createTable('DataTypeUsage',
                         [('symId'      , 'INTEGER'),
                          ('usage'       , 'TEXT', 'NOT NULL'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER', 'NOT NULL'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(symId)', 'REFERENCES DataType(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('EnumUsage',
                         [('symId'     , 'INTEGER'),
                          ('usage'       , 'TEXT', 'NOT NULL'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER', 'NOT NULL'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(symId)', 'REFERENCES DataTypeField(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('Function',
                         [('storageSpec'  , 'VARCHAR(8)'),
                          ('funcSpec'     , 'VARCHAR(6)'),
                          ('retType'      , 'VARCHAR(64)'),
                          ('funcTypeId'   , 'INTEGER'),
                          ('retRefType'   , 'VARCHAR(64)'),
                          ('name'         , 'VARCHAR(32)'),
                          ('isDef'        , 'INTEGER'),
                          ('fid'          , 'INTEGER'),
                          ('row'          , 'INTEGER'),
                          ('col'          , 'INTEGER'),
                          ('PRIMARY KEY'  , '(fid, row, col)'),
                          ('FOREIGN KEY'  , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY'  , '(funcTypeId)', 'REFERENCES Function(rowid)'),
                          ]
                         )

        self.createTable('FunctionParam',
                         [('type'       , 'VARCHAR(128)'),
                          ('funcTypeId' , 'INTEGER'),
                          ('refType'    , 'VARCHAR(64)'),
                          ('name'       , 'VARCHAR(64)'),
                          ('dim'        , 'VARCHAR(32)'),
                          ('fid'        , 'INTEGER', 'NOT NULL'),
                          ('row'        , 'INTEGER', 'NOT NULL'),
                          ('col'        , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY', '(fid, row, col)'),
                          ('FOREIGN KEY', '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY', '(funcTypeId)', 'REFERENCES Function(rowid)'),
                          ]
                         )

        self.createTable('FuncParamLink',
                         [('funcId'     , 'INTEGER', 'NOT NULL'),
                          ('paramId'    , 'INTEGER', 'NOT NULL'),
                          ('FOREIGN KEY', '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY', '(paramId)', 'REFERENCES FunctionParam(rowid)'),
                          ]
                         )

        self.createTable('FunctionUsage',
                         [('symId'       , 'INTEGER'),
                          ('expression'  , 'TEXT', 'NOT NULL'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER', 'NOT NULL'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(symId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('FunctionCall',
                         [('symId'       , 'INTEGER'),
                          ('expression'  , 'TEXT', 'NOT NULL'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER', 'NOT NULL'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(symId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('Typedef',
                         [('type'       , 'VARCHAR(64)'),
                          ('dataTypeId' , 'INTEGER'),
                          ('funcTypeId' , 'INTEGER'),
                          ('refType'    , 'VARCHAR(64)'),
                          ('name'       , 'VARCHAR(32)', 'NOT NULL'),
                          ('dim'        , 'VARCHAR(32)'),
                          ('fid'        , 'INTEGER', 'NOT NULL'),
                          ('row'        , 'INTEGER', 'NOT NULL'),
                          ('col'        , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY', '(name, fid)'),
                          ('FOREIGN KEY', '(dataTypeId)', 'REFERENCES DataType(rowid)'),
                          ('FOREIGN KEY', '(funcTypeId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY', '(fid)', 'REFERENCES File(rowid)'),
                          ]
                         )

        self.createTable('TypedefUsage',
                         [('symId'      , 'INTEGER'),
                          ('usage'       , 'TEXT', 'NOT NULL'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(symId)', 'REFERENCES Typedef(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('Variable',
                         [('storageClass', 'VARCHAR(8)'),
                          ('type'        , 'VARCHAR(64)'),
                          ('dataTypeId'  , 'INTEGER'),
                          ('funcTypeId'  , 'INTEGER'),
                          ('refType'     , 'VARCHAR(32)'),
                          ('name'        , 'VARCHAR(32)', 'NOT NULL'),
                          ('dim'         , 'VARCHAR(32)'),
                          ('initValue'   , 'TEXT'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(dataTypeId)', 'REFERENCES DataType(rowid)'),
                          ('FOREIGN KEY' , '(funcTypeId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('VariableUsage',
                         [('symId'       , 'INTEGER'),
                          ('usage'       , 'TEXT', 'NOT NULL'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(symId)', 'REFERENCES Variable(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('BuiltinType',
                         [('name', 'VARCHAR(64)'),
                          ('PRIMARY KEY', '(name)'),
                          ]
                         )

        self.createTable('BuiltinTypeUsage',
                         [('symId'       , 'INTEGER'),
                          ('usage'       , 'TEXT', 'NOT NULL'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER'),
                          ('blockId'     , 'INTEGER'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(symId)', 'REFERENCES Builtin(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('Label',
                         [('label'       , 'VARCHAR(64)', 'NOT NULL'),
                          ('expr'        , 'VARCHAR(64)'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER', 'NOT NULL'),
                          ('blockId'     , 'INTEGER', 'NOT NULL'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('Jump',
                         [('type'        , 'VARCHAR(8)', 'NOT NULL'),
                          ('labelId'     , 'VARCHAR(64)'),
                          ('expr'        , 'TEXT'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER', 'NOT NULL'),
                          ('blockId'     , 'INTEGER', 'NOT NULL'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(labelId)', 'REFERENCES Label(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('ControlStatement',
                         [('type'        , 'VARCHAR(8)', 'NOT NULL'),
                          ('init'        , 'VARCHAR(128)'),
                          ('cond'        , 'VARCHAR(256)'),
                          ('inc'         , 'VARCHAR(128)'),
                          ('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER', 'NOT NULL'),
                          ('blockId'     , 'INTEGER', 'NOT NULL'),
                          ('nestLevel'   , 'INTEGER', 'NOT NULL'),
                          ('nestIters'   , 'INTEGER', 'NOT NULL'),
                          ('nestSels'    , 'INTEGER', 'NOT NULL'),
                          ('row'         , 'INTEGER', 'NOT NULL'),
                          ('col'         , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(fid, row, col)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )

        self.createTable('ControlStatementLink',
                         [('parentCtrlId' , 'INTEGER'),
                          ('ctrlId'       , 'INTEGER', 'NOT NULL'),
                          ('FOREIGN KEY'  , '(parentCtrlId)', 'REFERENCES ControlStatement(rowid)'),
                          ('FOREIGN KEY'  , '(ctrlId)', 'REFERENCES ControlStatement(rowid)'),
                          ]
                         )

        self.createTable('SwitchCaseLink',
                         [('switchId'    , 'INTEGER', 'NOT NULL'),
                          ('labelId'     , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(switchId, labelId)'),
                          ('FOREIGN KEY' , '(switchId)', 'REFERENCES ControlStatement(rowid)'),
                          ('FOREIGN KEY' , '(labelId)', 'REFERENCES Label(rowid)'),
                          ]
                         )

        self.createTable('IfElseLink',
                         [('ifId'        , 'INTEGER'),
                          ('elseId'      , 'INTEGER', 'NOT NULL'),
                          ('PRIMARY KEY' , '(ifId, elseId)'),
                          ('FOREIGN KEY' , '(ifId)', 'REFERENCES ControlStatement(rowid)'),
                          ('FOREIGN KEY' , '(elseId)', 'REFERENCES ControlStatement(rowid)'),
                          ]
                         )

        self.createTable('Block',
                         [('fid'         , 'INTEGER', 'NOT NULL'),
                          ('funcId'      , 'INTEGER', 'NOT NULL'),
                          ('ctrlId'      , 'INTEGER'),
                          ('nestLevel'   , 'INTEGER', 'NOT NULL'),
                          ('startRow'    , 'INTEGER', 'NOT NULL'),
                          ('startCol'    , 'INTEGER', 'NOT NULL'),
                          ('endRow'      , 'INTEGER', 'NOT NULL'),
                          ('endCol'      , 'INTEGER', 'NOT NULL'),
                          ('FOREIGN KEY' , '(funcId)', 'REFERENCES Function(rowid)'),
                          ('FOREIGN KEY' , '(fid)', 'REFERENCES File(rowid)'),
                          ('FOREIGN KEY' , '(ctrlId)', 'REFERENCES ControlStatement(rowid)'),
                          ]
                         )

        self.createTable('BlockLink',
                         [('parentBlockId', 'INTEGER'),
                          ('blockId'      , 'INTEGER', 'NOT NULL'),
                          ('FOREIGN KEY'  , '(parentBlockId)', 'REFERENCES Block(rowid)'),
                          ('FOREIGN KEY'  , '(blockId)', 'REFERENCES Block(rowid)'),
                          ]
                         )


    def loadDB(self, dbPath):
        if self.cursor:
            self.cursor.close()

        if self.conn:
            self.conn.close()

        self.dbPath = dbPath

        self.conn = sqlite3.connect(dbPath)
        self.cursor = self.conn.cursor()

    def saveDB(self):
        self.conn.commit()

    def closeDB(self):
        if self.cursor:
            self.cursor.close()

        if self.conn:
            self.conn.close()

    def createTable(self, tableName, fields):
        cmd = 'CREATE TABLE %s (%s)' % (tableName, ', '.join([' '.join(field) for field in fields]))
        #print cmd
        self.cursor.execute(cmd)

    def addData(self, info):
        self.addFiles(info)

        includes_queue = deque()

        for filename in info.keys():
            root_fid = self.getFid(filename)
            root_info = info[filename]
            includes_queue.append((root_fid, 0, root_info['includes']))

            while includes_queue:
                parent_fid, depth, includes = includes_queue.popleft()

                for include in includes:
                    child_fid = self.getFid(include[1])
                    self.addInclude(root_fid, parent_fid, child_fid, include, depth)
                    child_info = include[-1]

                    if child_info:
                        self.addMacroDefs(child_fid, child_info['defines'])
                        self.addMacroUndefs(child_fid, child_info['undefs'])
                        self.addMacroCalls(child_fid, child_info['macroCalls'])

                        if child_info.has_key('pragmas'):
                            self.addPragma(child_fid, child_info['pragmas'])

                        if child_info.has_key('data_types'):
                            self.addDataTypes(child_fid, child_info['data_types'])
                            self.addTypedefs(child_fid, child_info['typedefs'])
                            self.addVariables(child_fid, child_info['variables'])
                            self.addFunctions(child_fid, child_info['function_prototypes'])
                            self.addFunctions(child_fid, child_info['function_definitions'], isDef=True)
                            for name, (_,_,_,func_info,_) in child_info['function_definitions'].items():
                                self.addFunctionDefInfo(child_fid, self.getFuncId(name, isDef=True), func_info)

                        includes_queue.append((child_fid, depth+1, child_info['includes']))

            self.addMacroDefs(root_fid, root_info['defines'])
            self.addMacroUndefs(root_fid, root_info['undefs'])
            self.addMacroCalls(root_fid, root_info['macroCalls'])

            if root_info.has_key('pragmas'):
                self.addPragma(root_fid, root_info['pragmas'])

            if root_info.has_key('data_types'):
                self.addDataTypes(root_fid, root_info['data_types'])
                self.addTypedefs(root_fid, root_info['typedefs'])
                self.addVariables(root_fid, root_info['variables'])
                self.addFunctions(root_fid, root_info['function_prototypes'])
                self.addFunctions(root_fid, root_info['function_definitions'], isDef=True)
                for name, (_,_,_,func_info,_) in root_info['function_definitions'].items():
                    self.addFunctionDefInfo(root_fid, self.getFuncId(name, isDef=True), func_info)

        for filename in info.keys():
            root_fid = self.getFid(filename)
            root_info = info[filename]
            includes_queue.append((root_fid, 0, root_info['includes']))

            while includes_queue:
                parent_fid, depth, includes = includes_queue.popleft()

                for include in includes:
                    child_fid = self.getFid(include[1])
                    child_info = include[-1]

                    if child_info:
                        if child_info.has_key('data_types'):
                            self.addSymbolUsages(child_fid, child_info['global_symbol_usage'])
                            for name, (_,_,_,func_info,_) in child_info['function_definitions'].items():
                                self.addFunctionUsageInfo(child_fid, self.getFuncId(name, isDef=True), func_info)

                        includes_queue.append((child_fid, depth+1, child_info['includes']))

            if root_info.has_key('data_types'):
                self.addSymbolUsages(root_fid, root_info['global_symbol_usage'])
                for name, (_,_,_,func_info,_) in root_info['function_definitions'].items():
                    #print name
                    #for k, v in func_info.items():
                    #    print k
                    #    print v
                    #print
                    self.addFunctionUsageInfo(root_fid, self.getFuncId(name, isDef=True), func_info)

    def addFunctionDefInfo(self, fid, funcId, funcInfo, blockId=None, numBlocks=0, numIterNest=0, numSelNest=0, ifId=None, ctrlId=None):
        if funcInfo.has_key('block'):
            blockId = self.addBlock(fid, funcId, ctrlId, funcInfo['block'], blockId, numBlocks)
            numBlocks += 1

        self.addVariables(fid, funcInfo['variables'], funcId, blockId)
        self.addLabels(fid, funcId, blockId, funcInfo['label'])

        if funcInfo.has_key('if'):
            for expr, if_info, if_pos, else_info, else_pos in funcInfo['if']:
                newIfId = self.addIf(fid, funcId, blockId, ifId, expr, if_pos, numIterNest, numSelNest)
                self.addCtrlStmtLink(ctrlId, newIfId)
                if if_info:
                    self.addFunctionDefInfo(fid, funcId, if_info, blockId, numBlocks, numIterNest, numSelNest+1, ctrlId=newIfId)
                if else_info:
                    if else_info.has_key('if'):
                        self.addFunctionDefInfo(fid, funcId, else_info, blockId, numBlocks, numIterNest, numSelNest, newIfId, ctrlId=ctrlId)
                    else:
                        newIfId = self.addIf(fid, funcId, blockId, newIfId, None, else_pos, numIterNest, numSelNest)
                        self.addCtrlStmtLink(ctrlId, newIfId)
                        self.addFunctionDefInfo(fid, funcId, else_info, blockId, numBlocks, numIterNest, numSelNest+1, ctrlId=newIfId)
        if funcInfo.has_key('switch'):
            for expr, info, pos in funcInfo['switch']:
                _ctrlId = self.addSwitch(fid, funcId, blockId, expr, pos, numIterNest, numSelNest)
                self.addCtrlStmtLink(ctrlId, _ctrlId)
                if info:
                    self.addFunctionDefInfo(fid, funcId, info, blockId, numBlocks, numIterNest, numSelNest+1, ctrlId=_ctrlId)
        if funcInfo.has_key('case') and ctrlId:
            self.addCases(fid, funcId, blockId, ctrlId, funcInfo['case'])
            for expr1, expr2, info, pos in funcInfo['case']:
                if info:
                    self.addFunctionDefInfo(fid, funcId, info, blockId, numBlocks, numIterNest, numSelNest)
        if funcInfo.has_key('default'):
            self.addDefaults(fid, funcId, blockId, ctrlId, funcInfo['default'])
            for info, pos in funcInfo['default']:
                if info:
                    self.addFunctionDefInfo(fid, funcId, info, blockId, numBlocks, numIterNest, numSelNest)
        if funcInfo.has_key('label'):
            for label, info, pos in funcInfo['label']:
                if info:
                    self.addFunctionDefInfo(fid, funcId, info, blockId, numBlocks, numIterNest, numSelNest)
        if funcInfo.has_key('for'):
            for expr1, expr2, expr3, info, pos in funcInfo['for']:
                _ctrlId = self.addFor(fid, funcId, blockId, expr1, expr2, expr3, pos, numIterNest, numSelNest)
                self.addCtrlStmtLink(ctrlId, _ctrlId)
                if info:
                    self.addFunctionDefInfo(fid, funcId, info, blockId, numBlocks, numIterNest+1, numSelNest, ctrlId=_ctrlId)
        if funcInfo.has_key('while'):
            for expr, info, pos in funcInfo['while']:
                _ctrlId = self.addWhile(fid, funcId, blockId, expr, pos, numIterNest, numSelNest)
                self.addCtrlStmtLink(ctrlId, _ctrlId)
                if info:
                    self.addFunctionDefInfo(fid, funcId, info, blockId, numBlocks, numIterNest+1, numSelNest, ctrlId=_ctrlId)
        if funcInfo.has_key('do'):
            for expr, info, pos in funcInfo['do']:
                _ctrlId = self.addDoWhile(fid, funcId, blockId, expr, pos, numIterNest, numSelNest)
                self.addCtrlStmtLink(ctrlId, _ctrlId)
                if info:
                    self.addFunctionDefInfo(fid, funcId, info, blockId, numBlocks, numIterNest+1, numSelNest, ctrlId=_ctrlId)

    def addFunctionUsageInfo(self, fid, funcId, funcInfo, blockId=None):
        if funcInfo.has_key('block'):
            funcInfo.has_key('block')
            s, t = funcInfo['block']
            self.cursor.execute('SELECT rowid FROM Block WHERE fid=? AND funcId=? AND startRow=? AND startCol=?',
                                (fid,
                                 funcId,
                                 s[0],
                                 s[1]
                                 ))
            blockId = self.cursor.fetchone()[0]

        self.addSymbolUsages(fid, funcInfo['global_symbol_usage'], funcId, blockId)
        self.addSymbolUsages(fid, funcInfo['local_symbol_usage'], funcId, blockId)
        self.addFunctionCalls(fid, funcId, blockId, funcInfo['function_calls'])
        self.addReturns(fid, funcId, blockId, funcInfo['return'])
        self.addGotos(fid, funcId, blockId, funcInfo['goto'])
        self.addContinues(fid, funcId, blockId, funcInfo['continue'])
        self.addBreaks(fid, funcId, blockId, funcInfo['break'])

        if funcInfo.has_key('if'):
            for expr, if_info, if_pos, else_info, else_pos in funcInfo['if']:
                if if_info: self.addFunctionUsageInfo(fid, funcId, if_info, blockId)
                if else_info: self.addFunctionUsageInfo(fid, funcId, else_info, blockId)
        if funcInfo.has_key('switch'):
            for expr, info, pos in funcInfo['switch']:
                if info: self.addFunctionUsageInfo(fid, funcId, info, blockId)
        if funcInfo.has_key('case'):
            for expr1, expr2, info, pos in funcInfo['case']:
                if info: self.addFunctionUsageInfo(fid, funcId, info, blockId)
        if funcInfo.has_key('label'):
            for label, info, pos in funcInfo['label']:
                if info: self.addFunctionUsageInfo(fid, funcId, info, blockId)
        if funcInfo.has_key('for'):
            for expr1, expr2, expr3, info, pos in funcInfo['for']:
                if info: self.addFunctionUsageInfo(fid, funcId, info, blockId)
        if funcInfo.has_key('while'):
            for expr, info, pos in funcInfo['while']:
                if info: self.addFunctionUsageInfo(fid, funcId, info, blockId)
        if funcInfo.has_key('do'):
            for expr, info, pos in funcInfo['do']:
                if info: self.addFunctionUsageInfo(fid, funcId, info, blockId)

    def addBlock(self, fid, funcId, ctrlId, block, parentBlockId, depth):
        self.cursor.execute('INSERT INTO Block VALUES (?,?,?,?,?,?,?,?)',
                (fid,
                 funcId,
                 ctrlId,
                 depth,
                 block[0][0],
                 block[0][1],
                 block[1][0],
                 block[1][1],
                 ))
        self.cursor.execute('SELECT last_insert_rowid()')
        blockId = self.cursor.fetchone()[0]
        self.cursor.execute('INSERT INTO BlockLink VALUES (?,?)', (parentBlockId, blockId))
        return blockId

    def addLabels(self, fid, funcId, blockId, labels):
        self.cursor.executemany('INSERT INTO Label VALUES (?,NULL,?,?,?,?,?)',
                [(l[0], fid, funcId, blockId, l[-1][0], l[-1][1]) for l in labels])

    def addCases(self, fid, funcId, blockId, switchId, cases):
        for case in cases:
            self.cursor.execute('INSERT INTO Label VALUES (?,?,?,?,?,?,?)',
                    ('case',
                     case[0] if not case[1] else '%s ... %s' % (case[0], case[1]),
                     fid,
                     funcId,
                     blockId,
                     case[-1][0],
                     case[-1][1]))
            self.cursor.execute('SELECT last_insert_rowid()')
            self.cursor.execute('INSERT INTO SwitchCaseLink VALUES (?,?)', (switchId, self.cursor.fetchone()[0]))

    def addDefaults(self, fid, funcId, blockId, switchId, defaults):
        for default in defaults:
            self.cursor.execute('INSERT INTO Label VALUES (?,NULL,?,?,?,?,?)',
                    ('default',
                     fid,
                     funcId,
                     blockId,
                     default[-1][0],
                     default[-1][1]))
            self.cursor.execute('SELECT last_insert_rowid()')
            self.cursor.execute('INSERT INTO SwitchCaseLink VALUES (?,?)', (switchId, self.cursor.fetchone()[0]))

    def addGotos(self, fid, funcId, blockId, gotos):
        for (label, pos) in gotos:
            self.cursor.execute('SELECT rowid FROM Label WHERE name=? AND fid=? AND funcId=?', (label, fid, funcId))
            ret = self.cursor.fetchall()
            if not ret:
                self.cursor.execute('SELECT rowid FROM Label WHERE name=? AND fid=?', (label, fid))
                ret = self.cursor.fetchall()
                if not ret:
                    self.cursor.execute('SELECT rowid FROM Label WHERE name=?', (label))
                    ret = self.cursor.fetchall()

            if ret:
                self.cursor.execute('INSERT INTO Jump VALUES (?,?,NULL,?,?,?,?,?)',
                                    ('goto', ret[0], fid, funcId, blockId, pos[0], pos[1]))

    def addContinues(self, fid, funcId, blockId, continues):
        self.cursor.executemany('INSERT INTO Jump VALUES (?,NULL,NULL,?,?,?,?,?)', 
                                [('continue', fid, funcId, blockId, c[0], c[1]) for c in continues])

    def addBreaks(self, fid, funcId, blockId, breaks):
        self.cursor.executemany('INSERT INTO Jump VALUES (?,NULL,NULL,?,?,?,?,?)', 
                                [('break', fid, funcId, blockId, c[0], c[1]) for c in breaks])

    def addCtrlStmtLink(self, parentCtrlId, childCtrlId):
        self.cursor.execute('INSERT INTO ControlStatementLink VALUES (?,?)', (parentCtrlId, childCtrlId))

    def addWhile(self, fid, funcId, blockId, expr, pos, numIterNest, numSelNest):
        self.cursor.execute('INSERT INTO ControlStatement VALUES (?,NULL,?,NULL,?,?,?,?,?,?,?,?)',
                            ('while',
                             expr,
                             fid,
                             funcId,
                             blockId,
                             numSelNest + numIterNest,
                             numIterNest,
                             numSelNest,
                             pos[0],
                             pos[1]))
        self.cursor.execute('SELECT last_insert_rowid()')
        return self.cursor.fetchone()[0]

    def addDoWhile(self, fid, funcId, blockId, expr, pos, numIterNest, numSelNest):
        self.cursor.execute('INSERT OR IGNORE INTO ControlStatement VALUES (?,NULL,?,NULL,?,?,?,?,?,?,?,?)',
                            ('do while',
                             expr,
                             fid,
                             funcId,
                             blockId,
                             numSelNest + numIterNest,
                             numIterNest,
                             numSelNest,
                             pos[0],
                             pos[1]))
        self.cursor.execute('SELECT last_insert_rowid()')
        return self.cursor.fetchone()[0]

    def addFor(self, fid, funcId, blockId, expr1, expr2, expr3, pos, numIterNest, numSelNest):
        self.cursor.execute('INSERT INTO ControlStatement VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                            ('for',
                             expr1,
                             expr2,
                             expr3,
                             fid,
                             funcId,
                             blockId,
                             numSelNest + numIterNest,
                             numIterNest,
                             numSelNest,
                             pos[0],
                             pos[1]))
        self.cursor.execute('SELECT last_insert_rowid()')
        return self.cursor.fetchone()[0]

    def addSwitch(self, fid, funcId, blockId, expr, pos, numIterNest, numSelNest):
        self.cursor.execute('INSERT INTO ControlStatement VALUES (?,NULL,?,NULL,?,?,?,?,?,?,?,?)',
                            ('switch',
                             expr,
                             fid,
                             funcId,
                             blockId,
                             numSelNest + numIterNest,
                             numIterNest,
                             numSelNest,
                             pos[0],
                             pos[1]))
        self.cursor.execute('SELECT last_insert_rowid()')
        return self.cursor.fetchone()[0]
        #switchId = self.cursor.fetchone()[0]
        #if caseInfo.has_key('case'):
        #    self.addCases(fid, funcId, switchId, caseInfo['case'])
        #if caseInfo.has_key('default'):
        #    self.addDefaults(fid, funcId, switchId, caseInfo['default'])
        #return switchId

    def addIf(self, fid, funcId, blockId, ifId, cond, pos, numIterNest, numSelNest):
        if ifId is None:
            type = 'if'
        elif ifId and cond:
            type = 'else if'
        else:
            type = 'else'

        self.cursor.execute('INSERT INTO ControlStatement VALUES (?,NULL,?,NULL,?,?,?,?,?,?,?,?)',
                            (type,
                             cond,
                             fid,
                             funcId,
                             blockId,
                             numSelNest + numIterNest,
                             numIterNest,
                             numSelNest,
                             pos[0],
                             pos[1]))
        self.cursor.execute('SELECT last_insert_rowid()')
        elifId = self.cursor.fetchone()[0]
        self.cursor.execute('INSERT INTO IfElseLink VALUES (?,?)',
                            (ifId, elifId))
        return elifId

    def insert(self, tbl, fmt, *values):
        self.cursor.execute('INSERT INTO %s VALUES (%s)' % (tbl, fmt), values)

    def insertMany(self, tbl, fmt, valueList):
        self.cursor.executemany('INSERT OR IGNORE INTO %s VALUES (%s)' % (tbl, fmt), valueList)
        #self.cursor.executemany('INSERT INTO %s VALUES (%s)' % (tbl, fmt), valueList)

    def select(self, tbl, fmt):
        self.cursor.execute('SELECT %s FROM %s' % (fmt, tbl))
        return self.cursor.fetchall()

    def addFiles(self, info):
        #
        # collect all files
        #
        files = set()
        for key in info.keys():
            files.add(key)
            stack = deque([info[key]['includes']])
            while stack:
                includes = stack.pop()
                for inc in includes:
                    if inc[-1]:
                        stack.append(inc[-1]['includes'])
                        files.add(inc[-1]['path'])

        fileInfos = deque()
        for path in sorted(files):
            if os.path.isfile(path):
                with open(path) as f:
                    data = f.read()
                    fileInfos.append((path, len(data), data.count('\n')+1, sha.new(data).hexdigest()))
            else:
                fileInfos.append((path, 0, 0, ''))

        self.insertMany('File',
                        '?,?,?,?,?',
                        [(path,
                          size,
                          numLn,
                          path.endswith('.c'),
                          sha1) for path, size, numLn, sha1 in fileInfos])

    def addMacroDefs(self, fid, macros):
        self.insertMany('MacroDef',
                        '?,?,?,?,?,?,?',
                        [(name,
                          None if params is None else '(%s)' % ', '.join(params),
                          val,
                          expanded_val,
                          fid,
                          pos[0],
                          pos[1],
                          ) for name, params, val, expanded_val, pos in macros])
        #print 'done'

    def addMacroUses(self, fid, MacroUse):
        for key, val in MacroUse.items():
            self.cursor.execute('SELECT m.rowid FROM MacroDef m, (SELECT rowid FROM File WHERE path=?) as f WHERE f.rowid=m.fid AND m.row=? AND m.col=?', (val[1], val[2][0], val[2][1]))
            mid = self.cursor.fetchall()
            if not mid:
                print key, val

    def addMacroCalls(self, fid, macroCalls):
        self.insertMany('MacroUsage',
                        '?,?,?,?',
                        [(name,
                          fid,
                          pos[0],
                          pos[1],
                          ) for name, pos in macroCalls])

    def addIncludes(self, fid, includes):
        self.insertMany('Include',
                        '?,?,?,?,?,?,?',
                        [(name,
                          val[0],
                          fid,
                          loc[0],
                          loc[1],
                          ) for name, val in includes.items() for loc in val[1]])
        #print 'done'

    def addInclude(self, root_fid, parent_fid, child_fid, include, depth):
        self.cursor.execute('INSERT INTO Include VALUES (?,?,?,?,?,?,?)',
                (include[0],    # path
                 child_fid,     # child_fid
                 root_fid,      # root_fid
                 depth,         # depth
                 parent_fid,    # parent_fid
                 include[2][0], # row
                 include[2][1], # col
                 ))

    def addMacroUndefs(self, fid, undefs):
        self.insertMany('MacroUndef',
                        '?,?,?,?',
                        [(name,
                          fid,
                          pos[0],
                          pos[1],
                          ) for name, pos in undefs])

    def addPragma(self, fid, pragmas):
        self.insertMany('Pragma',
                        '?,?,?,?',
                        [(val,
                          fid,
                          pos[0],
                          pos[1],
                          ) for val, pos in pragmas])

    def addDataTypes(self, fid, dataTypes):
        #for name, (type, fields, loc) in sorted(dataTypes.items(), key=lambda (k,v): v[-1][0]):
        for name, defs in sorted(dataTypes.items(), key=lambda (k,v): v[-1][0]):
            while defs:
                type, fields, loc = defs.popleft()
                self.addDataType(fid, type, name, fields, loc)

    def addDataType(self, fid, type, name, fields, loc, depth=0):
        #
        # check if the datatype already exists
        #
        self.cursor.execute('SELECT rowid FROM DataType WHERE fid=? AND row=? AND col=?',
                            (fid, loc[0], loc[1]))
        ret = self.cursor.fetchone()

        if ret:
            #
            # exist
            #
            return ret[0]

        #
        # add data type
        #
        self.cursor.execute('INSERT INTO DataType VALUES (?,?,?,?,?,?)',
                            (type, name, fields is not None, fid, loc[0], loc[1]))

        self.cursor.execute('SELECT last_insert_rowid()')
        dataTypeId = self.cursor.fetchone()[0]

        #
        # if there are fields, add them into DataTypeField table
        #
        while fields:
            field = fields.popleft()
            #
            # if the field is struct/union/enum
            #
            if field[1]:
                dataType = field[1]
                #
                # if it is nested structure/union
                #
                if dataType[2]:
                    #
                    # add it to DataType table
                    #
                    _dataTypeId = self.addDataType(fid, dataType[0], dataType[1], dataType[2], dataType[3], depth+1)

                    self.cursor.execute('INSERT INTO DataTypeField VALUES (?,?,NULL,?,?,?,?,?,?,?)',
                            (field[0],    # type
                             _dataTypeId, # data type ID
                             field[3],    # ref
                             field[4],    # name
                             field[5],    # dimension
                             field[6],    # value
                             fid,
                             field[7][0], # row
                             field[7][1], # col
                             ))
                else:
                    self.cursor.execute('INSERT OR IGNORE INTO DataTypeField VALUES (?,NULL,NULL,?,?,?,?,?,?,?)',
                            (field[0],    # type
                             field[3],    # ref
                             field[4],    # name
                             field[5],    # dimension
                             field[6],    # value
                             fid,
                             field[7][0], # row
                             field[7][1], # col
                             ))
            #
            # else if the field is function poitner
            #
            elif field[2]:
                # add function pointer
                funcType = field[2]
                #print '---',funcType
                funcId = self.addFunction(None, None, funcType, None, funcType[-1], fid)
                self.cursor.execute('INSERT OR IGNORE INTO DataTypeField VALUES (NULL,NULL,?,?,?,?,?,?,?,?)',
                        (funcId,
                         field[3],    # ref
                         field[4],    # name
                         field[5],    # dimension
                         field[6],    # value
                         fid,
                         field[7][0], # row
                         field[7][1], # col
                         ))
            else:
                self.cursor.execute('INSERT OR IGNORE INTO DataTypeField VALUES (?,NULL,NULL,?,?,?,?,?,?,?)',
                        (field[0],    # type
                         field[3],    # ref
                         field[4],    # name
                         field[5],    # dimension
                         field[6],    # value
                         fid,
                         field[7][0], # row
                         field[7][1], # col
                         ))
            #
            # link DataTYpe and DataTypeField
            #
            self.cursor.execute('SELECT last_insert_rowid()')
            fieldId = self.cursor.fetchone()[0]
            self.cursor.execute('INSERT INTO DataTypeLink VALUES (?,?,?)',
                    (dataTypeId,
                     fieldId,
                     depth,
                     #False,
                     ))

        return dataTypeId

    def addFunctions(self, fid, functions, isDef=False):
        if not functions:
            return

        iter = functions.itervalues()
        if isinstance(iter.next(), deque):
            for name, defs in functions.items():
                while defs:
                    storageSpec, funcSpec, funcType, pos = defs.popleft()
                    self.cursor.execute('SELECT rowid FROM Function WHERE fid=? AND row=? AND col=?',
                            (fid, pos[0], pos[1]))
                    if self.cursor.fetchall():
                        # exists
                        continue
                    self.addFunction(storageSpec, funcSpec, funcType, name, pos, fid, isDef)
        elif not isDef:
            for name, (storageSpec, funcSpec, funcType, pos) in functions.items():
                self.cursor.execute('SELECT rowid FROM Function WHERE fid=? AND row=? AND col=?',
                        (fid, pos[0], pos[1]))
                if self.cursor.fetchall():
                    # exists
                    continue
                self.addFunction(storageSpec, funcSpec, funcType, name, pos, fid, isDef)
        else:
            for name, (storageSpec, funcSpec, funcType, funcInfo, pos) in functions.items():
                self.cursor.execute('SELECT rowid FROM Function WHERE fid=? AND row=? AND col=?',
                        (fid, pos[0], pos[1]))
                if self.cursor.fetchall():
                    # exists
                    continue
                self.addFunction(storageSpec, funcSpec, funcType, name, pos, fid, isDef)

    def addFunction(self, storageSpec, funcSpec, funcType, name, pos, fid, isDef=False):
        retType, retRefType, params, _pos = funcType
        self.cursor.execute('SELECT rowid FROM Function WHERE fid=? AND row=? AND col=?',
                (fid, pos[0], pos[1]))
        ret = self.cursor.fetchall()
        if ret:
            # exists
            return ret[0][0]

        #print storageSpec, retType, retRefType, name, params, pos, _pos, fid
        if isinstance(retType, str):
            retFuncId = None
        else:
            retFuncId = self.addFunction(None, None, retType, None, _pos, fid)
            retType = None
        self.cursor.execute('INSERT INTO Function VALUES (?,?,?,?,?,?,?,?,?,?)',
                (storageSpec,
                 funcSpec,
                 retType,    # return type
                 retFuncId,  # return type func id
                 retRefType, # return ref type
                 name,
                 isDef,      # isDef
                 fid,        # fid
                 pos[0],     # row
                 pos[1],     # col
                 ))
        self.cursor.execute('SELECT last_insert_rowid()')
        funcId = self.cursor.fetchone()[0]
        while params:
            typeSpec, structUnionInfo, funcType, ref, name, dim, pos = params.popleft()
            if pos is None:
                pos = structUnionInfo[-1]
            self.cursor.execute('SELECT rowid FROM FunctionParam WHERE fid=? AND row=? AND col=?',
                    (fid, pos[0], pos[1]))
            if self.cursor.fetchall():
                continue

            if funcType is None:
                _funcId = None
            else:
                _funcId = self.addFunction(None, None, funcType, None, funcType[-1], fid)
                typeSpec = None

            self.cursor.execute('INSERT INTO FunctionParam VALUES (?,?,?,?,?,?,?,?)',
                    (typeSpec, # type
                     _funcId,  # funcId
                     ref,      # refType
                     name,     # name
                     dim,      # dim
                     fid,      # fid
                     pos[0],   # row
                     pos[1],   # col
                     ))
            self.cursor.execute('SELECT last_insert_rowid()')
            paramId = self.cursor.fetchone()[0]
            self.cursor.execute('INSERT INTO FuncParamLink VALUES (?,?)', (funcId, paramId))
        return funcId

    def addSymbolUsages(self, fid, usage, funcId=None, blockId=None):
        for (name, sym_type, sym_path, sym_pos), values in usage.items():
            if sym_type == BUILTIN:
                self.cursor.execute('INSERT OR IGNORE INTO BuiltinType VALUES (?)', (name,))
                self.cursor.execute('SELECT last_insert_rowid()')
                tableName = 'BuiltinTypeUsage'
            else:
                if sym_path:
                    self.cursor.execute('SELECT rowid FROM File WHERE path=?', (sym_path,))
                    sym_fid = self.cursor.fetchone()[0]
                else:
                    sym_fid = fid

                if sym_type == VARIABLE:
                    tableName = 'VariableUsage'
                    self.cursor.execute('SELECT rowid FROM Variable WHERE name=? AND fid=? AND row=? AND col=?',
                                        (name, sym_fid, sym_pos[0], sym_pos[1]))
                elif sym_type == FUNCTION:
                    tableName = 'FunctionUsage'
                    self.cursor.execute('SELECT rowid FROM Function WHERE name=? AND fid=? AND row=? AND col=?',
                                        (name, sym_fid, sym_pos[0], sym_pos[1]))
                elif sym_type == TYPEDEF:
                    tableName = 'TypedefUsage'
                    self.cursor.execute('SELECT rowid FROM Typedef WHERE name=? AND fid=?',
                                        (name, sym_fid))
                elif sym_type == DATA_TYPE:
                    tableName = 'DataTypeUsage'
                    self.cursor.execute('SELECT rowid FROM DataType WHERE name=? AND fid=? AND row=? AND col=?',
                                        (name, sym_fid, sym_pos[0], sym_pos[1]))
                else: # ENUM_TYPE
                    tableName = 'EnumUsage'
                    self.cursor.execute('SELECT rowid FROM DataTypeField WHERE name=? AND fid=? AND row=? AND col=?',
                                        (name, sym_fid, sym_pos[0], sym_pos[1]))

            ret = self.cursor.fetchone()
            self.cursor.executemany('INSERT OR IGNORE INTO %s VALUES (?,?,?,?,?,?,?)' % tableName,
                    [(None if not ret else ret[0], # symid
                      expr,        # expression
                      fid,         # fid
                      funcId,      # funcId
                      blockId,     # blockId
                      pos[0],      # row
                      pos[1],      # col
                      ) for expr, pos in values])

    def addFunctionCalls(self, fid, funcId, blockId, func_calls):
        for (name, sym_path, sym_pos), values in func_calls.items():
            if sym_path:
                self.cursor.execute('SELECT rowid FROM File WHERE path=?', (sym_path,))
                sym_fid = self.cursor.fetchone()[0]
                self.cursor.execute('SELECT rowid FROM Function WHERE fid=? AND row=? AND col=?',
                                    (sym_fid, sym_pos[0], sym_pos[1]))
                ret = self.cursor.fetchone()
            elif sym_pos:
                self.cursor.execute('SELECT rowid FROM Function WHERE fid=? AND row=? AND col=?',
                                    (fid, sym_pos[0], sym_pos[1]))
                ret = self.cursor.fetchone()
            else:
                self.cursor.execute('SELECT rowid FROM Function WHERE name=?',
                                    (name,))
                ret = self.cursor.fetchone()
            self.cursor.executemany('INSERT OR IGNORE INTO FunctionCall VALUES (?,?,?,?,?,?,?)',
                    [(None if not ret else ret[0],   # symId
                      expr,   # expression
                      fid,    # file ID
                      funcId, # function ID
                      blockId,# block ID
                      pos[0], # row
                      pos[1], # col
                      ) for expr, pos in values])

    def addTypedefs(self, fid, typedefs):
        for name, val in typedefs.items():
            #
            # if typedef of struct/union/enum
            #
            if val[1]:
                ## struct/union/enum
                dataType = val[1]
                #
                # if there are fields
                #
                if dataType[2]:
                    #
                    # if there is ident
                    #
                    if dataType[1]:
                        self.cursor.execute("SELECT rowid FROM DataType WHERE name=? AND hasFields=1", (dataType[1],))
                        dataTypeId = self.cursor.fetchone()[0]
                    else:
                        dataTypeId = self.addDataType(fid, dataType[0], dataType[1], dataType[2], dataType[3])
                    self.cursor.execute('INSERT OR IGNORE INTO Typedef VALUES (?,?,NULL,?,?,?,?,?,?)',
                            (val[0], # type
                             dataTypeId, # dataTypeId
                             val[3], # reference type
                             name,   # name
                             val[4], # dimension
                             fid,    # fid
                             val[-1][0], # row
                             val[-1][1], # col
                             ))
                else:
                    self.cursor.execute('INSERT OR IGNORE INTO Typedef VALUES (?,NULL,NULL,?,?,?,?,?,?)',
                            (val[0], # type
                             val[3], # reference type
                             name,   # name
                             val[4], # dimension
                             fid,    # fid
                             val[-1][0], # row
                             val[-1][1], # col
                             ))
            #
            # else if typedef of function pointer
            #
            elif val[2]:
                #
                # store function prototype
                #
                funcType = val[2]
                #print '***', funcType
                funcId = self.addFunction(None, None, funcType, name, val[-1], fid)
                self.cursor.execute('INSERT OR IGNORE INTO Typedef VALUES (NULL,NULL,?,?,?,?,?,?,?)',
                        (funcId,
                         val[3],     # ref
                         name,       # name
                         val[4],     # dimension
                         fid,
                         val[-1][0], # row
                         val[-1][1], # col
                         ))
            else:
                self.cursor.execute('INSERT OR IGNORE INTO Typedef VALUES (?,NULL,NULL,?,?,?,?,?,?)',
                        (val[0],     # type
                         val[3],     # reference type
                         name,       # name
                         val[4],     # dimension
                         fid,        # fid
                         val[-1][0], # row
                         val[-1][1], # col
                         ))

    def addVariables(self, fid, variables, funcId=None, blockId=None):
        for name, vals in variables.items():
            for val in vals:
                self.cursor.execute("SELECT rowid FROM Variable WHERE fid=? AND row=? AND col=?",
                                    (fid, val[-1][0], val[-1][1]))
                if self.cursor.fetchall():
                    continue
                if val[2]:
                    ## struct/union/enum
                    dataType = val[2]
                    #
                    # if there are fields
                    #
                    if dataType[2]:
                        #
                        # if there is ident
                        #
                        if dataType[1]:
                            self.cursor.execute("SELECT rowid FROM DataType WHERE name=? AND hasFields=1", (dataType[1],))
                            dataTypeId = self.cursor.fetchone()[0]
                        else:
                            dataTypeId = self.addDataType(fid, dataType[0], dataType[1], dataType[2], dataType[3])
                        self.cursor.execute('INSERT OR IGNORE INTO Variable VALUES (?,?,?,NULL,?,?,?,?,?,?,?,?,?)',
                                (val[0],     # storage class
                                 val[1],     # type
                                 dataTypeId, # dataTypeId
                                 val[4],     # reference type
                                 name,       # name
                                 val[5],     # dimension
                                 val[6],     # initial value
                                 fid,        # fid
                                 funcId,     # funcId
                                 blockId,    # blockId
                                 val[-1][0], # row
                                 val[-1][1], # col
                                 ))
                    else:
                        self.cursor.execute('INSERT OR IGNORE INTO Variable VALUES (?,?,NULL,NULL,?,?,?,?,?,?,?,?,?)',
                                (val[0],     # storage class
                                 val[1],     # type
                                 val[4],     # reference type
                                 name,       # name
                                 val[5],     # dimension
                                 val[6],     # initial value
                                 fid,        # fid
                                 funcId,     # funcId
                                 blockId,    # blockId
                                 val[-1][0], # row
                                 val[-1][1], # col
                                 ))
                elif val[3]:
                    #
                    # store function prototype
                    #
                    funcType = val[3]
                    #print '***', funcType
                    funcTypeId = self.addFunction(None, None, funcType, name, val[-1], fid)
                    self.cursor.execute('INSERT OR IGNORE INTO Variable VALUES (?,NULL,NULL,?,?,?,?,?,?,?,?,?,?)',
                            (val[0],     # storage class
                             funcTypeId, # function ID
                             val[4],     # ref
                             name,       # name
                             val[5],     # dimension
                             val[6],     # initial value
                             fid,        # fid
                             funcId,     # funcId
                             blockId,    # blockId
                             val[-1][0], # row
                             val[-1][1], # col
                             ))
                else:
                    self.cursor.execute('INSERT INTO Variable VALUES (?,?,NULL,NULL,?,?,?,?,?,?,?,?,?)',
                            (val[0],     # storage class
                             val[1],     # type
                             val[4],     # reference type
                             name,       # name
                             val[5],     # dimension
                             val[6],     # initial value
                             fid,        # fid
                             funcId,     # funcId
                             blockId,    # blockId
                             val[-1][0], # row
                             val[-1][1], # col
                             ))

    def addReturns(self, fid, funcId, blockId, returns):
        self.cursor.executemany('INSERT INTO Jump VALUES (?,NULL,?,?,?,?,?,?)',
                [('return',
                  r[0],
                  fid,
                  funcId,
                  blockId,
                  r[1][0],
                  r[1][1]
                  ) for r in returns])

    def getFid(self, path):
        self.cursor.execute('SELECT rowid FROM File WHERE path=?', (path,))
        ret = self.cursor.fetchone()
        return None if not ret else ret[0]

    def getFuncId(self, func_name, isDef=False):
        self.cursor.execute('SELECT rowid FROM Function WHERE name=? AND isDef=?', (func_name,isDef))
        ret = self.cursor.fetchone()
        return None if not ret else ret[0]

    def getMacros(self):
        self.cursor.execute('SELECT * FROM MacroDef')
        return self.cursor.fetchall()

    def getMacro(self, macroName):
        self.cursor.execute(
        '''
        SELECT a1.name,
               a1.params,
               a1.value,
               a1.expandedValue,
               a1.symbolsUsed,
               a2.path,
               a1.row,
               a1.col
        FROM MacroDef a1, File a2, File a3
        where name=? and a1.fid=a2.fid
        ''', (macroName,))
        return self.cursor.fetchone()

    def getTableList(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return self.cursor.fetchall()


    def getTableData(self, tableName):
        self.cursor.execute("SELECT * FROM %s ORDER BY rowid" % tableName)
        return self.cursor.fetchall()

    def getTableInfo(self, tableName):
        self.cursor.execute("PRAGMA table_info(%s)" % tableName)
        return self.cursor.fetchall()

    def getProjectProfile(self):
        profiles = {}
        #linkage = {}

        for fid,path,numLines in self.cursor.execute('SELECT rowid,path,numLines FROM File').fetchall():
            profiles[fid] = (path, numLines, self.getFileProfile(fid))
            #linkage[fid] = {'used':set(), 'use':profiles[fid][1]['dependent_files'], 'include':profiles[fid][1]['include']}

        #for fid, val in linkage.items():
        #    for _fid in val['use']:
        #        linkage[_fid]['used'].add(fid)

        #for k, v in linkage.items():
        #    print k, profiles[k][0], v

        return profiles

    def getFileProfile(self, fid):
        profile = {}
        #profile['macro_def'] = [(name,params,value,self.getFilesUsingMacro(name,fid)) for name,params,value in self.getMacroDefs(fid)]
        profile['macro_def'] = self.getMacroDefs(fid)
        profile['macro_undef'] = self.getMacroUndefs(fid)
        macro_used = self.getMacroUsage(fid)
        profile['macro_usage'] = macro_used
        #profile['typedef'] = [(id,type,name,self.getFilesUsingTypedef(id)) for id,type,name in self.getTypedefs(fid)]
        profile['typedef'] = self.getTypedefs(fid)
        typedef_used = self.getTypedefUsage(fid)
        profile['typedef_usage'] = typedef_used
        #profile['datatype'] = [(id,type,name,self.getFilesUsingDataType(id)) for id,type,name in self.getDataTypes(fid)]
        profile['datatype'] = self.getDataTypes(fid)
        #profile['enum'] = [(id,name,val,self.getFilesUsingEnum(id)) for id,name,val in self.getEnums(fid)]
        profile['enum'] = self.getEnums(fid)
        datatype_used = self.getDataTypeUsage(fid)
        profile['datatype_usage'] = datatype_used
        enum_used = self.getEnumUsage(fid)
        profile['enum_usage'] = enum_used
        #profile['func'] = [(id,name,isDef,self.getFilesUsingFunc(name)) for id,name,isDef in self.getFunctions(fid)]
        profile['func'] = self.getFunctions(fid)
        func_used = self.getFunctionUsage(fid)
        profile['func_usage'] = func_used
        func_calls = self.getFunctionCalls(fid)
        profile['func_calls'] = func_calls
        extern_vars = self.getExternVariables(fid)
        profile['extern_var'] = extern_vars
        #profile['global_var'] = [(id,cls,name,self.getFilesUsingVariable(id)) for id,cls,name in self.getGlobalVariables(fid)]
        profile['global_var'] = self.getGlobalVariables(fid)
        vars_used = self.getVariableUsage(fid)
        profile['var_usage'] = vars_used
        included_fids = self.getIncludes(fid)
        #profile['include'] = (included_fids, self.getFilesIncludingFile(fid))
        profile['include'] = included_fids
        dependent_fids = set([])
        dependent_fids.update([f for _,f in macro_used if f != fid and f is not None])
        dependent_fids.update([f for _,_,f in typedef_used if f != fid and f is not None])
        dependent_fids.update([f for _,_,f in datatype_used if f != fid and f is not None])
        dependent_fids.update([f for _,_,f in enum_used if f != fid and f is not None])
        dependent_fids.update([f for _,_,f in func_used if f != fid and f is not None])
        dependent_fids.update([f for _,f in extern_vars if f != fid and f is not None])
        dependent_fids.update([f for _,_,f in vars_used if f != fid and f is not None])

        profile['files_used'] = dependent_fids & set(self.getHeaderFiles())
        profile['files_linking'] = dependent_fids & set(self.getSourceFiles())

        #for k,v in sorted(profile.items(),key=lambda (k,v): k):
        #    print '================================================================================'
        #    print '\t',k, len(v)
        #    print '--------------------------------------------------------------------------------'
        #    print v
        return profile

    def getSourceFiles(self):
        ret = self.cursor.execute('SELECT rowid FROM File WHERE isSrc=1').fetchall()
        return None if not ret else [r[0] for r in ret]

    def getHeaderFiles(self):
        ret = self.cursor.execute('SELECT rowid FROM File WHERE isSrc=0').fetchall()
        return None if not ret else [r[0] for r in ret]

    def getIncludes(self, fid):
        return self.cursor.execute('SELECT DISTINCT(path_fid) FROM Include WHERE fid=?', (fid,)).fetchall()

    def getFilePath(self, fid):
        return self.cursor.execute('SELECT path FROM File WHERE rowid=?', (fid,)).fetchone()[0]

    def getMacroDefs(self, fid):
        return self.cursor.execute('SELECT name,params,value FROM MacroDef WHERE fid=?', (fid,)).fetchall()

    def getMacroUndefs(self, fid):
        return self.cursor.execute('SELECT name FROM MacroUndef WHERE fid=?', (fid,)).fetchall()

    def getMacroUsage(self, fid):
        return self.cursor.execute('''
                SELECT DISTINCT(MU.name), M.fid
                FROM MacroUsage MU LEFT OUTER JOIN MacroDef M on MU.name=M.name
                WHERE MU.fid=? and (M.fid=MU.fid or M.fid is NULL or M.fid in (SELECT path_fid FROM Include WHERE root_fid=MU.fid))
                ''', (fid,)).fetchall()

    def getDataTypes(self, fid):
        return self.cursor.execute('SELECT rowid,type,name FROM DataType WHERE fid=?', (fid,)).fetchall()

    def getTypedefs(self, fid):
        return self.cursor.execute('SELECT rowid,type,name FROM Typedef WHERE fid=?', (fid,)).fetchall()

    def getTypedefUsage(self, fid):
        return self.cursor.execute(
                '''
                SELECT TU.symId,TU.usage,T.fid
                FROM TypedefUsage TU INNER JOIN Typedef T on TU.symId=T.rowid
                WHERE TU.fid=?
                ''', (fid,)).fetchall()

    def getDataTypeUsage(self, fid):
        return self.cursor.execute(
                '''
                SELECT DU.symId,DU.usage,D.fid
                FROM DataTypeUsage DU INNER JOIN DataType D on DU.symId=D.rowid
                WHERE DU.fid=?
                ''', (fid,)).fetchall()

    def getEnums(self, fid):
        return self.cursor.execute(
                '''
                SELECT F.rowid,F.name,F.value
                FROM (DataType T INNER JOIN DataTypeLink L ON T.rowid=L.dataTypeId)
                    INNER JOIN DataTypeField F ON L.fieldId=F.rowid
                WHERE T.fid=? AND T.type="enum"
                ''', (fid,)).fetchall()

    def getEnumUsage(self, fid):
        return self.cursor.execute(
                '''
                SELECT E.symId,E.usage,D.fid
                FROM EnumUsage E INNER JOIN DataTypeField D on E.symId=D.rowid
                WHERE E.fid=?
                ''', (fid,)).fetchall()

    def getFunctions(self, fid):
        return self.cursor.execute(
                '''
                SELECT rowid,name,isDef
                FROM Function
                WHERE fid=? AND NOT rowid IN (
                    SELECT DISTINCT(funcTypeId)
                    FROM Typedef
                    WHERE funcTypeId is not NULL
                    )
                ''', (fid,)).fetchall()

    def getMainFile(self):
        ret = self.cursor.execute('''SELECT fid FROM Function WHERE name="main"''').fetchone()
        return None if ret is None else ret[0]

    def getFunctionUsage(self, fid):
        return self.cursor.execute(
                '''
                SELECT FU.symId,FU.expression,F1.fid
                FROM Function F1, FunctionUsage FU INNER JOIN Function F2 on FU.symId=F2.rowid
                WHERE FU.fid=? AND F1.name=F2.name
                ''', (fid,)).fetchall()

    def getFunctionCalls(self, fid):
        return self.cursor.execute(
                '''
                SELECT FU.symId,FU.expression,F.fid
                FROM FunctionCall FU INNER JOIN Function F on FU.symId=F.rowid
                WHERE FU.fid=?
                ''', (fid,)).fetchall()

    def getGlobalVariables(self, fid):
        return self.cursor.execute('SELECT rowid,storageClass,name FROM Variable WHERE fid=? and storageClass!="extern" and funcId is NULL', (fid,)).fetchall()

    def getExternVariables(self, fid):
        return self.cursor.execute(
                '''
                SELECT V1.name,V2.fid
                FROM Variable V1, Variable V2
                WHERE V1.fid=? and V1.storageClass="extern" and V1.name=V2.name and V2.storageClass is NULL
                ''', (fid,)).fetchall()

    def getLocalVariables(self, fid):
        return self.cursor.execute('SELECT storageClass,name FROM Variable WHERE fid=? and funcId is not NULL', (fid,)).fetchall()

    def getVariableUsage(self, fid):
        return self.cursor.execute(
                '''
                SELECT VU.symId,VU.usage,V1.fid
                FROM Variable V1, VariableUsage VU INNER JOIN Variable V2 on VU.symId=V2.rowid
                WHERE VU.fid=? AND V1.name=V2.name AND (V2.storageClass!="extern" OR (V2.storageClass="extern" AND V1.storageClass!="extern"))
                ''', (fid,)).fetchall()

    def getFilesIncludingFile(self, fid):
        return self.cursor.execute(
                '''
                SELECT DISTINCT(root_fid)
                FROM Include
                WHERE path_fid=?
                ''', (fid,)).fetchall()

    def getFilesUsingMacro(self, name, fid):
        return self.cursor.execute(
                '''
                SELECT DISTINCT(MU.fid)
                FROM MacroUsage MU INNER JOIN MacroDef M on MU.name=M.name
                WHERE M.name=?
                ''', (name,)).fetchall()

    def getFilesUsingTypedef(self, id):
        return self.cursor.execute(
                '''
                SELECT DISTINCT(TU.fid)
                FROM TypedefUsage TU INNER JOIN Typedef T on TU.symId=T.rowid
                WHERE T.rowid=?
                ''', (id,)).fetchall()

    def getFilesUsingDataType(self, id):
        return self.cursor.execute(
                '''
                SELECT DISTINCT(DU.fid)
                FROM DataTypeUsage DU INNER JOIN DataType D on DU.symId=D.rowid
                WHERE D.rowid=?
                ''', (id,)).fetchall()

    def getFilesUsingEnum(self, id):
        return self.cursor.execute(
                '''
                SELECT DISTINCT(U.fid)
                FROM EnumUsage U INNER JOIN DataTypeField F on U.symId=F.rowid
                WHERE F.rowid=?
                ''', (id,)).fetchall()
    def getFilesUsingFunc(self, name):
        return self.cursor.execute(
                '''
                SELECT DISTINCT(FU.fid)
                FROM FunctionUsage FU INNER JOIN Function F on FU.symId=F.rowid
                WHERE F.name=?
                ''', (name,)).fetchall()

    def getFilesUsingVariable(self, id):
        return self.cursor.execute(
                '''
                SELECT DISTINCT(VU.fid)
                FROM VariableUsage VU INNER JOIN Variable V on VU.symId=V.rowid
                WHERE V.rowid=?
                ''', (id,)).fetchall()

    def getFunctionProfile(self, funcId):
        pass

