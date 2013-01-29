from collections import deque, defaultdict
import os
from xml.dom import minidom
import logging

from token_iter import TokenIterator
from scanner_types import *
from parser_types import *


logger = logging.getLogger('parser')
logger.setLevel(logging.INFO)

# create console handler and set level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(funcName)-33s:%(lineno)4d:%(message)s'))
logger.addHandler(ch)

INDENT = '   '


class Parser():
    global logger

    @staticmethod
    def getBuiltinTypes():
        builtin_types = set([
                '__builtin_va_list',
                ])
        return builtin_types

    def __init__(self, builtinTypes=None, outDir=None, logLevel=None, logPath="/var/log/parser.log", externalLogger=None):
        self.types                 = set()
        self.struct_union_enum_set = set()
        self.locals                = defaultdict(tuple)
        self.locals_set            = set()
        self.globals               = defaultdict(tuple)
        self.globals_set           = set()
        self.symbols_used          = set()
        self.builtin_types         = set(builtinTypes) if builtinTypes is not None else self.__class__.getBuiltinTypes()
        self.outDir                = outDir

        if externalLogger:
            externalLogger.setLevel(logging.INFO)
            externalLogger.setFormatter(logging.Formatter('%(levelname)-7s:%(name)s:%(message)s'))
            logger.addHandler(externalLogger)

        if logLevel:
            logger.setLevel(eval('logging.%s' % logLevel))

        if os.path.exists(logPath):
            os.remove(logPath)

        if self.outDir and not os.path.exists(self.outDir):
            os.makedirs(self.outDir)

        # add log file handler
        fh = logging.FileHandler(logPath)
        fh.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(funcName)-33s:%(lineno)4d:%(message)s"))
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

    def parse(self, ppInfo):
        logger.info('parse %s' % ppInfo['path'])

        self.types.clear()
        self.types.update(self.builtin_types)
        self.struct_union_enum_set.clear()
        self.globals.clear()
        self.globals.update((t, (BUILTIN, 'builtin', (0,0))) for t in self.builtin_types)
        self.globals_set.clear()

        self._parse(ppInfo)

        return ppInfo

    def _parse(self, info, indent=''):
        for include in info['includes']:
            if include[-1]:
                self._parse(include[-1], '%s%s'%(indent,INDENT))

        logger.info('%s_parse %s' % (indent, info['path']))

        if not info['tokens']:
            del info['tokens']
            return

        info['typedefs'] = defaultdict(tuple)
        info['data_types'] = defaultdict(deque)
        info['function_prototypes'] = defaultdict(deque)
        info['function_definitions'] = defaultdict(tuple)
        info['variables'] = defaultdict(deque)
        info['global_symbol_usage'] = defaultdict(deque)

        tree = deque()
        tokIter = TokenIterator(info['tokens'])

        if self.outDir:
            doc = minidom.Document()
            rootElem = doc.createElement('PARSE_TREE')

        while tokIter.lookaheadToken(1):
            assert self.external_declaration(tokIter, tree, info), 'failed to parse @ %s' % info['path']
            node = tree.pop()
            if self.outDir: self.save_parse_tree(doc, rootElem, node)
            #self.print_parse_tree(node)
            self.extract_info(node, info)
            #raw_input()
            #print

        if self.outDir:
            doc.appendChild(rootElem)
            f = open('%s/%s.xml' % (self.outDir, info['path'].replace(os.path.sep, '_').strip('_')), 'w')
            f.write(doc.toprettyxml(indent='    '))
            f.close()

        del info['tokens']

    def print_parse_tree(self, tree, indent=''):
        if len(tree) == 4:
            logger.debug('%s%s' % (indent, str(tree)))
        else:
            logger.debug('%s%s' % (indent, node_type_to_str[tree[NODE_TYPE]]))
            for node in tree[NODE_VALUE]:
                self.print_parse_tree(node, '%s|%s'%(indent,'  '))

    def save_parse_tree(self, doc, parentElem, node):
        if len(node) == 4:
            parentElem.appendChild(doc.createTextNode(node[TOK_VALUE]))
        else:
            elem = doc.createElement(node_type_to_str[node[NODE_TYPE]])
            for n in node[NODE_VALUE]:
                self.save_parse_tree(doc, elem, n)
            parentElem.appendChild(elem)

    def get_node(self, node, node_type):
        '''
        Traverse nodes using tail-recursive DFS (non-destructive)
        '''
        if node[NODE_TYPE] == node_type:
            return node
        elif len(node) == 2:
            for n in node[NODE_VALUE]:
                ret = self.get_node(n, node_type)
                if ret:
                    return ret
        return None

    def extract_string(self, node):
        '''
        Traverse nodes using DFS (non-destructive)
        '''
        return node[TOK_VALUE] if len(node) == 4 else ' '.join([self.extract_string(n) for n in node[NODE_VALUE] if n])

    def extract_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'extract_info'))
        n = node[NODE_VALUE].popleft()
        if n[NODE_TYPE] == NODE_DECLARATION:
            self.declaration_info(n, info, indent='%s%s'%(indent,INDENT))
        elif n[NODE_TYPE] == NODE_FUNCTION_DEFINITION:
            self.function_definition_info(n, info, indent='%s%s'%(indent,INDENT))

    def declaration_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'declaration_info'))

        self.extract_symbol_usage(node, self.extract_string(node), info)

        nodes = node[NODE_VALUE]
        storage_spec, func_spec, type_spec, struct_union_enum_type, type_pos = self.declaration_specifiers_info(nodes.popleft(), info, indent='%s%s'%(indent,INDENT))

        if len(nodes) == 1:
            #
            # if sturct/union/enum and there is ident
            #
            if struct_union_enum_type and struct_union_enum_type[1]:
                if struct_union_enum_type[2]:
                    self.struct_union_enum_set.add(struct_union_enum_type[1])
                    self.globals[struct_union_enum_type[1]] = (DATA_TYPE, info['path'], struct_union_enum_type[3])
                info['data_types'][struct_union_enum_type[1]].append((struct_union_enum_type[0],
                                                                      struct_union_enum_type[2],
                                                                      struct_union_enum_type[3],
                                                                      ))
            return

        #
        # if sturct/union/enum and there are ident and fields
        #
        if struct_union_enum_type and struct_union_enum_type[1] and struct_union_enum_type[2]:
            self.struct_union_enum_set.add(struct_union_enum_type[1])
            self.globals[struct_union_enum_type[1]] = (DATA_TYPE, info['path'], struct_union_enum_type[3])
            info['data_types'][struct_union_enum_type[1]].append((struct_union_enum_type[0],
                                                                  struct_union_enum_type[2],
                                                                  struct_union_enum_type[3],
                                                                  ))

        init_declarator_list = nodes.popleft()

        for init_declarator_node in [n for n in init_declarator_list[NODE_VALUE] if n[NODE_TYPE] == NODE_INIT_DECLARATOR]:
            init_declarator_value = init_declarator_node[NODE_VALUE]
            funcType, ref, nameTok, dim = self.declarator_info(init_declarator_value.popleft(), type_spec, info, indent='%s%s'%(indent,INDENT))

            init_val = None if not init_declarator_value else self.extract_string(init_declarator_value[1])

            if storage_spec and storage_spec[TOK_TYPE] == TOK_TYPEDEF:
                self.types.add(nameTok[TOK_VALUE])
                self.globals[nameTok[TOK_VALUE]] = (TYPEDEF, info['path'], nameTok[TOK_ROW:])
                logger.debug('types: %s' % (str(self.types)))

                info['typedefs'][nameTok[TOK_VALUE]] = (
                        type_spec,
                        struct_union_enum_type,
                        funcType,
                        ref,
                        dim,
                        nameTok[TOK_ROW:],
                        )
                continue

            if funcType is not None and not ref:
                self.globals_set.add(nameTok[TOK_VALUE])
                self.globals[nameTok[TOK_VALUE]] = (FUNCTION, info['path'], nameTok[TOK_ROW:])
                info['function_prototypes'][nameTok[TOK_VALUE]].append((
                        storage_spec if storage_spec is None else storage_spec[TOK_VALUE],
                        func_spec,
                        funcType,
                        nameTok[TOK_ROW:],
                        ))
            else:
                self.globals_set.add(nameTok[TOK_VALUE])
                self.globals[nameTok[TOK_VALUE]] = (VARIABLE, info['path'], nameTok[TOK_ROW:])
                info['variables'][nameTok[TOK_VALUE]].append((
                        storage_spec if storage_spec is None else storage_spec[TOK_VALUE],
                        type_spec,
                        struct_union_enum_type,
                        funcType,
                        ref,
                        dim,
                        init_val,
                        nameTok[TOK_ROW:],
                        ))

    def declaration_specifiers_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'declaration_specifiers_info'))
        storage_spec = None
        func_spec = None
        type_spec = ''
        struct_union_enum_type = None
        type_pos = None

        for n in node[NODE_VALUE]:
            if n[NODE_TYPE] == NODE_STORAGE_CLASS_SPECIFIER:
                storage_spec = n[NODE_VALUE][0]
            elif n[NODE_TYPE] == NODE_FUNCTION_SPECIFIER:
                func_spec = n[NODE_VALUE][0][TOK_VALUE]
            elif n[NODE_TYPE] == NODE_TYPE_QUALIFIER:
                type_spec = n[NODE_VALUE][0][TOK_VALUE] if not type_spec else \
                            '%s %s' % (type_spec, n[NODE_VALUE][0][TOK_VALUE])
                if not type_pos:
                    type_pos = n[NODE_VALUE][0][TOK_ROW:]
            elif n[NODE_TYPE] == NODE_TYPE_SPECIFIER:
                n = n[NODE_VALUE][0]
                if n[NODE_TYPE] == NODE_STRUCT_OR_UNION_SPECIFIER or n[NODE_TYPE] == NODE_ENUM_SPECIFIER:
                    if n[NODE_TYPE] == NODE_STRUCT_OR_UNION_SPECIFIER:
                        type, ident, decl_list, fields = self.struct_or_union_specifier_info(n, info, indent='%s%s'%(indent,INDENT))
                    else:
                        type, ident, decl_list, fields = self.enum_specifier_info(n, info, indent='%s%s'%(indent,INDENT))

                    if ident:
                        type_spec = '%s %s' % (type[TOK_VALUE], ident[TOK_VALUE]) if not type_spec else \
                                    '%s %s %s' % (type_spec, type[TOK_VALUE], ident[TOK_VALUE])
                    else:
                        type_spec = type[TOK_VALUE] if not type_spec else \
                                    '%s %s' % (type_spec, type[TOK_VALUE])

                    struct_union_enum_type = (type[TOK_VALUE],
                                              None if not ident else ident[TOK_VALUE],
                                              fields,
                                              type[TOK_ROW:] if not ident else ident[TOK_ROW:]
                                              )

                    if not type_pos:
                        type_pos = type[TOK_ROW:]
                    if not ident and not decl_list:
                        raise Exception()
                else:
                    type_spec = n[TOK_VALUE] if not type_spec else \
                                '%s %s' % (type_spec, n[TOK_VALUE])
                    if not type_pos:
                        type_pos = n[TOK_ROW:]
            else:
                raise Exception('Unexpected node in specifier_qualifier_list: %s' % str(n))

        return storage_spec, func_spec, type_spec, struct_union_enum_type, type_pos

    def struct_or_union_specifier_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'struct_or_union_specifier_info'))
        nv = node[NODE_VALUE]
        type = nv.popleft()
        ident = None if nv[0][TOK_TYPE] != TOK_IDENTIFIER else nv.popleft()
        decl_list = None if not nv or nv[1][NODE_TYPE] != NODE_STRUCT_DECLARATION_LIST else nv[1]

        return type, ident, decl_list, None if not decl_list else self.struct_declaration_list_info(decl_list, info, indent='%s%s'%(indent,INDENT))

    def enum_specifier_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'enum_specifier_info'))
        nv = node[NODE_VALUE]
        type = nv.popleft()
        ident = None if nv[0][TOK_TYPE] != TOK_IDENTIFIER else nv.popleft()
        decl_list = None if not nv or nv[1][NODE_TYPE] != NODE_ENUMERATOR_LIST else nv[1]

        return type, ident, decl_list, None if not decl_list else self.enumerator_list_info(decl_list, info, indent='%s%s'%(indent,INDENT))

    def declarator_info(self, node, type_spec, info, indent=''):
        logger.debug('%s%s' % (indent, 'declarator_info'))
        stack = deque()

        self._declarator_info(node, stack, info, indent='%s%s'%(indent,INDENT))

        if len(stack) > 1:
            _, _, nameTok, _, _ = stack.pop()
        else:
            nameTok = None

        ref, param, _, dim, pos = stack.pop()

        if param is not None:
            #
            # function
            #
            return deque([type_spec, ref, param, pos]), None, nameTok, None

        #
        # function pointer
        #
        type = None
        ptr = None
        while stack:
            _ref, param, _, _, _pos = stack.pop()
            if type:
                ptr[0] = deque([None, _ref, param, pos])
                ptr = ptr[0]
            else:
                type = deque([None, _ref, param, pos])
                ptr = type
            pos = _pos

        if ptr:
            ptr[0] = type_spec
        return type, ref, nameTok, dim

    def _declarator_info(self, node, stack, info, pos=None, indent=''):
        logger.debug('%s%s' % (indent, '_declarator_info'))
        nv = node[NODE_VALUE]

        ref = None if nv[0][NODE_TYPE] != NODE_POINTER else self.extract_string(nv.popleft())

        if nv and nv[0][NODE_TYPE] == NODE_DIRECT_DECLARATOR:
            self.direct_declarator_info(nv.popleft(), stack, info, indent='%s%s'%(indent,INDENT))

        suffix_node = None if not nv or nv[0][NODE_TYPE] != NODE_DIRECT_DECLARATOR_SUFFIX else nv.popleft()

        if not suffix_node:
            stack.appendleft((ref,
                              None,
                              None,
                              None,
                              pos
                              ))
        elif suffix_node[NODE_VALUE][0][NODE_TYPE] == NODE_PARAMETER_SPECIFIER:
            parameter_specifier_value = suffix_node[NODE_VALUE][0][NODE_VALUE]
            stack.appendleft((ref,
                              deque() if len(parameter_specifier_value) != 3 else self.parameter_list_info(parameter_specifier_value[1], info, indent='%s%s'%(indent,INDENT)),
                              None,
                              None,
                              pos
                              ))
        else:
            stack.appendleft((ref,
                              None,
                              None,
                              self.extract_string(suffix_node),
                              pos
                              ))

    def direct_declarator_info(self, node, stack, info, indent=''):
        logger.debug('%s%s' % (indent, 'direct_declarator_info'))
        nv = node[NODE_VALUE]
        tok = nv.popleft()

        if tok[TOK_TYPE] == TOK_IDENTIFIER:
            stack.appendleft((None, None, tok, None, None))
        elif tok[TOK_TYPE] & TOK_OPERATOR:
            self._declarator_info(nv.popleft(), stack, info, pos=tok[TOK_ROW:], indent='%s%s'%(indent,INDENT))

    def parameter_list_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'parameter_list_info'))
        params = deque()
        for parameter_declaration_node in [n for n in node[NODE_VALUE] if n[NODE_TYPE] == NODE_PARAMETER_DECLARATION or n[NODE_TYPE] == TOK_ELLIPSIS]:
            if parameter_declaration_node[TOK_TYPE] == TOK_ELLIPSIS:
                params.append((parameter_declaration_node[TOK_VALUE],
                               None,
                               None,
                               None,
                               None,
                               None,
                               parameter_declaration_node[TOK_ROW:]
                               ))
                break

            parameter_declaration_value = parameter_declaration_node[NODE_VALUE]
            _, _, type_spec, struct_union_enum_type, type_pos = self.declaration_specifiers_info(parameter_declaration_value.popleft(), info, indent='%s%s'%(indent,INDENT))

            if not parameter_declaration_value:
                params.append((type_spec,
                               struct_union_enum_type,
                               None,
                               None,
                               None,
                               None,
                               type_pos
                               ))
                continue

            declarator_node = parameter_declaration_value.popleft()
            if declarator_node[NODE_TYPE] == NODE_DECLARATOR:
                funcType, ref, nameTok, dim = self.declarator_info(declarator_node, type_spec, info, indent='%s%s'%(indent,INDENT))

                params.append((type_spec,
                               struct_union_enum_type,
                               funcType,
                               ref,
                               None if nameTok is None else nameTok[TOK_VALUE],
                               dim,
                               type_pos if nameTok is None else nameTok[TOK_ROW:]
                               ))
            elif declarator_node[NODE_TYPE] == NODE_ABSTRACT_DECLARATOR:
                print declarator_node
                raw_input()

        return params

    def struct_declaration_list_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'struct_declaration_list_info'))
        fields = deque()
        for struct_declaration_node in node[NODE_VALUE]:
            _, _, type_spec, struct_union_enum_type, type_pos = self.declaration_specifiers_info(struct_declaration_node[NODE_VALUE].popleft(), info, indent='%s%s'%(indent,INDENT))

            if len(struct_declaration_node[NODE_VALUE]) == 1:
                fields.append((type_spec,
                               struct_union_enum_type,
                               None,
                               None,
                               None,
                               None,
                               None,
                               type_pos
                               ))
                continue

            struct_declarator_list_node = struct_declaration_node[NODE_VALUE].popleft()

            for struct_declarator_node in [n for n in struct_declarator_list_node[NODE_VALUE] if n[NODE_TYPE] == NODE_STRUCT_DECLARATOR]:
                nv = struct_declarator_node[NODE_VALUE]
                funcType, ref, nameTok, dim = (None, None, None, None) if nv[0][NODE_TYPE] != NODE_DECLARATOR else self.declarator_info(nv.popleft(), type_spec, info, indent='%s%s'%(indent,INDENT))

                fields.append((type_spec,
                               struct_union_enum_type,
                               funcType,
                               ref,
                               None if not nameTok else nameTok[TOK_VALUE],
                               dim,
                               None if not nv else self.extract_string(nv[1]),
                               type_pos if not nameTok else nameTok[TOK_ROW:]
                               ))
        return fields

    def enumerator_list_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'enumerator_list_info'))
        fields = deque()
        for enum in node[NODE_VALUE]:
            if not (enum[TOK_TYPE] & TOK_OPERATOR):
                nameTok = enum[NODE_VALUE][0]
                fields.append((None,
                               None,
                               None,
                               None,
                               nameTok[TOK_VALUE],
                               None,
                               None if len(enum[NODE_VALUE]) == 1 else self.extract_string(enum[NODE_VALUE][2]),
                               nameTok[TOK_ROW:]
                               ))
                self.extract_symbol_usage(enum, self.extract_string(enum), info)
                self.globals_set.add(nameTok[TOK_VALUE])
                self.globals[nameTok[TOK_VALUE]] = (ENUM_TYPE, info['path'], nameTok[TOK_ROW:])
        return fields

    def function_definition_info(self, node, info, indent=''):
        logger.debug('%s%s' % (indent, 'function_definition_info'))

        self.locals.clear()
        self.locals_set.clear()

        nv = node[NODE_VALUE]
        compound_statement_node = nv.pop()

        self.extract_symbol_usage(node, self.extract_string(node), info)

        storage_spec, func_spec, type_spec, struct_union_enum_type, type_pos = self.declaration_specifiers_info(nv.popleft(), info, indent='%s%s'%(indent,INDENT))

        funcType, ref, nameTok, dim = self.declarator_info(nv.popleft(), type_spec, info, indent='%s%s'%(indent,INDENT))
        #print 'decl:', funcType, ref, nameTok, dim

        if nv and nv[0][NODE_TYPE] == NODE_DECLARATION_LIST:
            decl_list = nv.popleft()
            print decl_list
            raw_input()

        self.globals_set.add(nameTok[TOK_VALUE])
        self.globals[nameTok[TOK_VALUE]] = (FUNCTION, info['path'], nameTok[TOK_ROW:])

        funcInfo = defaultdict(deque)
        funcInfo['variables'] = defaultdict(deque)
        funcInfo['function_calls'] = defaultdict(deque)
        funcInfo['global_symbol_usage'] = defaultdict(deque)
        funcInfo['local_symbol_usage'] = defaultdict(deque)

        if funcType:
            #
            # add parameters to local variables of this function
            #
            for param in funcType[2]:
                if param[4]:
                    self.locals[param[4]] = (VARIABLE, param[-1])
                    self.locals_set.add(param[4])
                    funcInfo['variables'][param[4]].append((
                            None,
                            param[0],
                            param[1],
                            param[2],
                            param[3],
                            param[5],
                            None,
                            param[-1],
                            ))

        self.compound_statement_info(compound_statement_node, funcInfo, indent='%s%s'%(indent,INDENT))

        info['function_definitions'][nameTok[TOK_VALUE]] = (
            storage_spec if storage_spec is None else storage_spec[TOK_VALUE],
            func_spec,
            funcType,
            funcInfo,
            nameTok[TOK_ROW:],
        )

    def compound_statement_info(self, node, funcInfo, indent=''):
        logger.debug('%s%s' % (indent, 'compound_statement_info'))
        funcInfo['block'] = (node[NODE_VALUE][0][TOK_ROW:], node[NODE_VALUE][-1][TOK_ROW:])

        if node[NODE_VALUE][1][NODE_TYPE] != NODE_BLOCK_ITEM_LIST:
            return

        for block_item_node in node[NODE_VALUE][1][NODE_VALUE]:
            n = block_item_node[NODE_VALUE].popleft()

            if n[NODE_TYPE] == NODE_DECLARATION:
                self.local_declaration_info(n, funcInfo, indent='%s%s'%(indent,INDENT))
            else:
                self.statement_info(n, funcInfo, indent='%s%s'%(indent,INDENT))

    def statement_info(self, node, funcInfo, indent=''):
        logger.debug('%s%s' % (indent, 'statement_info'))
        n = node[NODE_VALUE].popleft()
        if n[NODE_TYPE] == NODE_COMPOUND_STATEMENT:
            temp = self.locals.copy()
            self.compound_statement_info(n, funcInfo, indent='%s%s'%(indent,INDENT))
            self.locals = temp
            self.locals_set = set(self.locals)
        elif n[NODE_TYPE] == NODE_EXPRESSION_STATEMENT:
            self.expression_statement_info(n, funcInfo, indent='%s%s'%(indent,INDENT))
        elif n[NODE_TYPE] == NODE_SELECTION_STATEMENT:
            self.selection_statement_info(n, funcInfo, indent='%s%s'%(indent,INDENT))
        elif n[NODE_TYPE] == NODE_ITERATION_STATEMENT:
            self.iteration_statement_info(n, funcInfo, indent='%s%s'%(indent,INDENT))
        elif n[NODE_TYPE] == NODE_LABELED_STATEMENT:
            self.labeled_statement_info(n, funcInfo, indent='%s%s'%(indent,INDENT))
        else:
            self.jump_statement_info(n, funcInfo, indent='%s%s'%(indent,INDENT))

    def local_declaration_info(self, node, funcInfo, indent=''):
        logger.debug('%s%s' % (indent, 'local_declaration_info'))
        self.extract_symbol_usage(node, self.extract_string(node), funcInfo)

        nodes = node[NODE_VALUE]
        storage_spec, func_spec, type_spec, struct_union_enum_type, type_pos = self.declaration_specifiers_info(nodes.popleft(), funcInfo, indent='%s%s'%(indent,INDENT))

        if len(nodes) == 1:
            #
            # if sturct/union/enum and there is ident
            #
            if struct_union_enum_type and struct_union_enum_type[1]:
                funcInfo['data_types'][struct_union_enum_type[1]].append((struct_union_enum_type[0],
                                                                      struct_union_enum_type[2],
                                                                      struct_union_enum_type[3],
                                                                      ))
            return

        #
        # if sturct/union/enum and there are ident and fields
        #
        if struct_union_enum_type and struct_union_enum_type[1] and struct_union_enum_type[2]:
            funcInfo['data_types'][struct_union_enum_type[1]].append((struct_union_enum_type[0],
                                                                  struct_union_enum_type[2],
                                                                  struct_union_enum_type[3],
                                                                  ))

        init_declarator_list = nodes.popleft()

        for init_declarator_node in [n for n in init_declarator_list[NODE_VALUE] if n[NODE_TYPE] == NODE_INIT_DECLARATOR]:
            init_declarator_value = init_declarator_node[NODE_VALUE]
            funcType, ref, nameTok, dim = self.declarator_info(init_declarator_value.popleft(), type_spec, funcInfo, indent='%s%s'%(indent,INDENT))

            if init_declarator_value:
                initializer_node = init_declarator_value[1]
                init_val = self.extract_string(initializer_node)
            else:
                init_val = None

            self.locals[nameTok[TOK_VALUE]] = (VARIABLE, nameTok[TOK_ROW:])
            self.locals_set.add(nameTok[TOK_VALUE])
            funcInfo['variables'][nameTok[TOK_VALUE]].append((
                    storage_spec if storage_spec is None else storage_spec[TOK_VALUE],
                    type_spec,
                    struct_union_enum_type,
                    funcType,
                    ref,
                    dim,
                    init_val,
                    nameTok[TOK_ROW:],
                    ))

    def extract_symbol_usage(self, node, node_str, funcInfo):
        self.symbols_used.clear()
        self._extract_symbol_usage_helper(node, node_str, funcInfo)

    def _extract_symbol_usage_helper(self, node, node_str, funcInfo):
        #print node_type_to_str.get(node[NODE_TYPE], node)

        if node[NODE_TYPE] == NODE_UNARY_EXPRESSION:
            #print 'UNARY_EXPRESSION', node
            self._extract_symbol(node, node_str, funcInfo)
            if len(node) == 2:
                for n in node[NODE_VALUE]:
                    self._extract_symbol_usage_helper(n, node_str, funcInfo)
        elif node[NODE_TYPE] == NODE_TYPE_NAME or node[NODE_TYPE] == NODE_DIRECT_DECLARATOR or node[NODE_TYPE] == NODE_TYPE_SPECIFIER:
            #print 'TYPE_NAME/DIRECT_DECLARATOR/TYPE_SPECIFIER', node
            self._extract_type(node, node_str, funcInfo)
            if len(node) == 2:
                for n in node[NODE_VALUE]:
                    self._extract_symbol_usage_helper(n, node_str, funcInfo)
        elif node[NODE_TYPE] == NODE_STRUCT_OR_UNION_SPECIFIER or node[NODE_TYPE] == NODE_ENUM_SPECIFIER:
            #print 'STRUCT/UNION/ENUM', node
            self._extract_struct_union_enum_type(node, node_str, funcInfo)
            if len(node) == 2:
                for n in node[NODE_VALUE]:
                    self._extract_symbol_usage_helper(n, node_str, funcInfo)
        elif len(node) == 2:
            for n in node[NODE_VALUE]:
                self._extract_symbol_usage_helper(n, node_str, funcInfo)

    def _extract_symbol(self, node, node_str, funcInfo):
        ident = self.get_node(node, TOK_IDENTIFIER)
        if not ident or ident in self.symbols_used:
            return

        if ident[TOK_VALUE] in self.locals_set:
            self.symbols_used.add(ident)
            type, loc = self.locals[ident[TOK_VALUE]]
            path = None
            usage = (node_str, ident[TOK_ROW:])
            funcInfo['local_symbol_usage'][(ident[TOK_VALUE], type, path, loc)].append(usage)
            #print 'local symbol:', ident, usage
        elif ident[TOK_VALUE] in self.globals_set:
            self.symbols_used.add(ident)
            type, path, loc = self.globals[ident[TOK_VALUE]]
            usage = (node_str, ident[TOK_ROW:])
            funcInfo['global_symbol_usage'][(ident[TOK_VALUE], type, path, loc)].append(usage)
            #print 'global symbol:', ident, usage
        else:
            path = None
            loc = None
            usage = (node_str, ident[TOK_ROW:])
            #print 'type not found:', ident

        nv = node[NODE_VALUE]
        if len(nv) > 1 and nv[1][NODE_TYPE] == NODE_POSTFIX_EXPRESSION_SUFFIX and nv[1][NODE_VALUE][0][TOK_VALUE] == '(':
            self.symbols_used.add(ident)
            funcInfo['function_calls'][(ident[TOK_VALUE], path, loc)].append(usage)
            #print 'function call', usage

    def _extract_type(self, node, node_str, funcInfo):
        ident = self.get_node(node, TOK_IDENTIFIER)
        if not ident or ident in self.symbols_used:
            return

        if ident[TOK_VALUE] in self.types:
            self.symbols_used.add(ident)
            type, path, loc = self.globals[ident[TOK_VALUE]]
            usage = (node_str, ident[TOK_ROW:])
            funcInfo['global_symbol_usage'][(ident[TOK_VALUE], type, path, loc)].append(usage)
            #print 'global type symbol:', ident, usage

    def _extract_struct_union_enum_type(self, node, node_str, funcInfo):
        ident = None if len(node[NODE_VALUE]) == 1 else node[NODE_VALUE][1]
        if not ident or ident in self.symbols_used:
            return

        if ident[TOK_VALUE] in self.struct_union_enum_set:
            self.symbols_used.add(ident)
            type, path, loc = self.globals[ident[TOK_VALUE]]
            usage = (node_str, ident[TOK_ROW:])
            funcInfo['global_symbol_usage'][(ident[TOK_VALUE], type, path, loc)].append(usage)
            #print 'struct/union/enum symbol:', ident, usage

    def expression_statement_info(self, statement, funcInfo, indent=''):
        '''
        extract expression_statement info
        : (expression)? ';'
        '''
        logger.debug('%s%s' % (indent, 'expression_statement_info'))
        if len(statement[NODE_VALUE]) == 1:
            return
        node = statement[NODE_VALUE].popleft()
        self.extract_symbol_usage(node, self.extract_string(node), funcInfo)

    def selection_statement_info(self, statement, funcInfo, indent=''):
        '''
        extract selection_statement info
        : IF '(' expression ')' statement (ELSE statement)?
        | SWITCH '(' expression ')' statement
        '''
        logger.debug('%s%s' % (indent, 'selection_statement_info'))
        info = defaultdict(deque)
        info['variables'] = defaultdict(deque)
        info['function_calls'] = defaultdict(deque)
        info['global_symbol_usage'] = defaultdict(deque)
        info['local_symbol_usage'] = defaultdict(deque)

        nodes = statement[NODE_VALUE]
        tok = nodes[0]
        exp_str = self.extract_string(nodes[2])

        if tok[TOK_TYPE] == TOK_IF:
            if len(nodes) > 5:
                else_stmt_node = nodes.pop()
                elseTok = nodes.pop()
                stmt_node = nodes.pop()
                self.extract_symbol_usage(nodes[2], self.extract_string(statement), funcInfo)
                self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))

                else_info = defaultdict(deque)
                else_info['variables'] = defaultdict(deque)
                else_info['function_calls'] = defaultdict(deque)
                else_info['global_symbol_usage'] = defaultdict(deque)
                else_info['local_symbol_usage'] = defaultdict(deque)
                self.statement_info(else_stmt_node, else_info, indent='%s%s'%(indent,INDENT))
            else:
                elseTok = None
                stmt_node = nodes.pop()
                self.extract_symbol_usage(nodes[2], self.extract_string(statement), funcInfo)
                self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
                else_info = None

            funcInfo['if'].append((exp_str, info, tok[TOK_ROW:], else_info, None if not elseTok else elseTok[TOK_ROW:]))
        else:
            stmt_node = nodes.pop()
            self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
            funcInfo['switch'].append((exp_str, info, tok[TOK_ROW:]))

    def iteration_statement_info(self, statement, funcInfo, indent=''):
        '''
        extract iteration_statement info
        : WHILE '(' expression ')' statement
        | DO statement WHILE '(' expression ')' ';'
        | FOR '(' (expression_statement | declaration) expression_statement (expression)? ')' statement
        '''
        logger.debug('%s%s' % (indent, 'iteration_statement_info'))
        info = defaultdict(deque)
        info['variables'] = defaultdict(deque)
        info['function_calls'] = defaultdict(deque)
        info['global_symbol_usage'] = defaultdict(deque)
        info['local_symbol_usage'] = defaultdict(deque)

        nodes = statement[NODE_VALUE]
        tok = nodes[0]
        if tok[TOK_TYPE] == TOK_WHILE:
            stmt_node = nodes.pop()
            exp_str = self.extract_string(nodes[2])
            self.extract_symbol_usage(nodes[2], self.extract_string(statement), funcInfo)
            self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
            funcInfo['while'].append((exp_str, info, tok[TOK_ROW:]))
        elif tok[TOK_TYPE] == TOK_DO:
            self.statement_info(nodes[1], info, indent='%s%s'%(indent,INDENT))
            nodes.popleft()
            nodes.popleft()
            exp_str = self.extract_string(nodes[2])
            self.extract_symbol_usage(nodes[2], self.extract_string(statement), funcInfo)
            funcInfo['do'].append((exp_str, info, tok[TOK_ROW:]))
        else:
            stmt_node = nodes.pop()
            exp_str1 = self.extract_string(nodes[2]).rstrip(';')

            if nodes[2][NODE_TYPE] == NODE_EXPRESSION_STATEMENT:
                self.expression_statement_info(nodes[2], funcInfo, indent='%s%s'%(indent,INDENT))
            else:
                self.local_declaration_info(nodes[2], funcInfo, indent='%s%s'%(indent,INDENT))

            exp_str2 = self.extract_string(nodes[3]).rstrip(';')
            self.expression_statement_info(nodes[3], funcInfo, indent='%s%s'%(indent,INDENT))

            if nodes[4][NODE_TYPE] == NODE_EXPRESSION:
                exp_str3 = self.extract_string(nodes[4])
                self.extract_symbol_usage(nodes[4], self.extract_string(statement), funcInfo)
                self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
            else:
                exp_str3 = None
                self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))

            funcInfo['for'].append((None if not exp_str1 else exp_str1,
                                    None if not exp_str2 else exp_str2,
                                    None if not exp_str3 else exp_str3,
                                    info,
                                    tok[TOK_ROW:]))

    def labeled_statement_info(self, statement, funcInfo, indent=''):
        '''
        extract labeled_statement info
        : (IDENTIFIER|DEFAULT) ':' statement
        | CASE constant_expression ('...' constant_expression)? ':' statement # C extension (Case Range)
        '''
        logger.debug('%s%s' % (indent, 'labeled_statement_info'))
        info = defaultdict(deque)
        info['variables'] = defaultdict(deque)
        info['function_calls'] = defaultdict(deque)
        info['global_symbol_usage'] = defaultdict(deque)
        info['local_symbol_usage'] = defaultdict(deque)

        nodes = statement[NODE_VALUE]
        stmt_node = nodes.pop()
        tok = nodes[0]
        if tok[TOK_TYPE] == TOK_CASE:
            exp_str1 = self.extract_string(nodes[1])
            self.extract_symbol_usage(nodes[1], self.extract_string(statement), funcInfo)
            if nodes[2][TOK_TYPE] == TOK_ELLIPSIS:
                exp_str2 = self.extract_string(nodes[3])
                self.extract_symbol_usage(nodes[3], self.extract_string(statement), funcInfo)
                self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
            else:
                exp_str2 = None
                self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
            funcInfo['case'].append((exp_str1, exp_str2, info, tok[TOK_ROW:]))
        elif tok[TOK_TYPE] == TOK_DEFAULT:
            self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
            funcInfo['default'].append((info, tok[TOK_ROW:]))
        else:
            self.statement_info(stmt_node, info, indent='%s%s'%(indent,INDENT))
            funcInfo['label'].append((tok[TOK_VALUE], info, tok[TOK_ROW:]))

    def jump_statement_info(self, statement, funcInfo, indent=''):
        '''
        extract jump_statement info
        : GOTO IDENTIFIER ';'
        | (CONTINUE|BREAK) ';'
        | RETURN (expression)? ';'
        '''
        logger.debug('%s%s' % (indent, 'jump_statement_info'))
        nodes = statement[NODE_VALUE]
        tok = nodes[0]
        if tok[TOK_TYPE] == TOK_GOTO:
            ident = nodes[1]
            funcInfo['goto'].append((ident[TOK_VALUE], tok[TOK_ROW:]))
        elif tok[TOK_TYPE] == TOK_RETURN:
            if nodes[1][NODE_TYPE] == NODE_EXPRESSION:
                exp = nodes[1]
                funcInfo['return'].append((self.extract_string(exp),
                                           tok[TOK_ROW:]
                                           ))
                self.extract_symbol_usage(exp, self.extract_string(statement), funcInfo)
            else:
                funcInfo['return'].append((None, tok[TOK_ROW:]))
        else:
            funcInfo[tok[TOK_VALUE]].append(tok[TOK_ROW:])

    def external_declaration(self, tokIter, tree, info, indent=''):
        '''
        : declaration
        | function_definition

        declaration
        : declaration_specifiers (declarator ('=' initializer)? (',' declarator ('=' initializer)?)*)? ';'

        function_definition
        : declaration_specifiers declarator ((declartion)+)? '{' (block_item_list)? '}'
        '''
        logger.debug('%s%s' % (indent, 'external_declaration'))
        nodes = deque()

        assert self.declaration_specifiers(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse external_declaration @ %s' % info['path']

        token = tokIter.lookaheadToken(1)
        
        if token[TOK_VALUE] == ';':
            assert self.declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse external_declaration @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_EXTERNAL_DECLARATION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True

        assert self.declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse external_declaration @ %s' % info['path']

        token = tokIter.lookaheadToken(1)
        logger.debug('%s%s' % (indent, str(token)))
        if token[TOK_VALUE] == '=' or token[TOK_VALUE] == ',' or token[TOK_VALUE] == ';':
            assert self.declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse external_declaration @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_EXTERNAL_DECLARATION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif self.function_definition(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_EXTERNAL_DECLARATION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True

        logger.debug('%s%s' % (indent, False))
        return False

    def declaration(self, tokIter, tree, info, indent=''):
        '''
        : declaration_specifiers (init_declarator_list)? ';'
        '''
        logger.debug('%s%s' % (indent, 'declaration'))
        if tree and tree[0][NODE_TYPE] == NODE_DECLARATION_SPECIFIERS:
            decl_spec = tree.popleft()
        elif self.declaration_specifiers(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            decl_spec = tree.pop()
        else:
            logger.debug('%s%s' % (indent, False))
            return False

        init_decl_list = None if not self.init_declarator_list(tokIter, tree, info, '%s%s'%(indent,INDENT)) else tree.pop()

        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == ';':
            nodes = deque()
            nodes.append(decl_spec)
            if init_decl_list:
                nodes.append(init_decl_list)
            nodes.append(tokIter.getToken())
            tree.append((NODE_DECLARATION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            tree.append(decl_spec)
            if init_decl_list:
                tree.append(init_decl_list)
            logger.debug('%s%s' % (indent, False))
            return False

    def function_definition(self, tokIter, tree, info, indent=''):
        '''
        : declaration_specifiers declarator (declaration_list)? compound_statement
        '''
        logger.debug('%s%s' % (indent, 'function_definition'))
        nodes = deque()
        if tree and tree[0][NODE_TYPE] == NODE_DECLARATION_SPECIFIERS:
            nodes.append(tree.popleft())
        elif not self.declaration_specifiers(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
        else:
            logger.debug('%s%s' % (indent, False))
            return False

        if tree and tree[0][NODE_TYPE] == NODE_DECLARATOR:
            nodes.append(tree.popleft())
        elif self.declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
        else:
            logger.debug('%s%s' % (indent, False))
            return False

        if self.declaration_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        if not self.compound_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes.append(tree.pop())
        tree.append((NODE_FUNCTION_DEFINITION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def declaration_specifiers(self, tokIter, tree, info, indent=''):
        '''
        : (storage_class_specifier | type_specifier | type_qualifier | function_specifier)+
        '''
        logger.debug('%s%s' % (indent, 'declaration_specifiers'))
        nodes = deque()
        while True:
            token = tokIter.lookaheadToken(1)
            if token[TOK_TYPE] & TOK_STORAGE_CLASS and \
                    self.storage_class_specifier(tokIter, nodes, info, '%s%s'%(indent,INDENT)): 
                pass
            elif token[TOK_TYPE] == TOK_INLINE and \
                    self.function_specifier(tokIter, nodes, info, '%s%s'%(indent,INDENT)):
                pass
            elif token[TOK_TYPE] & TOK_TYPE_QUAL and \
                    self.type_qualifier(tokIter, nodes, info, '%s%s'%(indent,INDENT)):
                pass
            elif (token[TOK_TYPE] & TOK_TYPE_SPEC or \
                    (token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types and \
                        (not nodes or nodes[-1][NODE_TYPE] != NODE_TYPE_SPECIFIER))) and \
                 self.type_specifier(tokIter, nodes, info, '%s%s'%(indent,INDENT)):
                pass
            else:
                #if token[TOK_TYPE] == TOK_IDENTIFIER:
                #    print token
                #    print self.types.keys()
                break

        if nodes:
            tree.append((NODE_DECLARATION_SPECIFIERS, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def parameter_list(self, tokIter, tree, info, indent=''):
        '''
        : parameter_declaration (',' parameter_declaration)* (',' ELLIPSIS)?

        First Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER
        INLINE
        CONST, RESTRICT, VOLATILE
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION, ENUM 
        IDENTIFIER (TYPE_NAME)
        '''
        logger.debug('%s%s' % (indent, 'parameter_list'))
        nodes = deque()
        if not self.parameter_declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes.append(tree.pop())
        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] == ',':
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)
            if token[TOK_TYPE] != TOK_ELLIPSIS:
                assert self.parameter_declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse parameter_list @ %s' % info['path']
                nodes.append(tree.pop())
                token = tokIter.lookaheadToken(1)
            else:
                nodes.append(tokIter.getToken())
                break

        tree.append((NODE_PARAMETER_LIST, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def parameter_declaration(self, tokIter, tree, info, indent=''):
        '''
        : declaration_specifiers (declarator | abstract_declarator)?

        First Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER
        INLINE
        CONST, RESTRICT, VOLATILE
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION, ENUM 
        IDENTIFIER (TYPE_NAME)
        '''
        logger.debug('%s%s' % (indent, 'parameter_declaration'))
        if not self.declaration_specifiers(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())
        if self.declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
        elif self.abstract_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
        tree.append((NODE_PARAMETER_DECLARATION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def abstract_declarator(self, tokIter, tree, info, indent=''):
        '''
        : pointer (direct_abstract_declarator (direct_abstract_declarator_suffix)?)?
        | direct_abstract_declarator (direct_abstract_declarator_suffix)?

        First Set:
        '*', '[', '('
        '''
        logger.debug('%s%s' % (indent, 'abstract_declarator'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '*' and self.pointer(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            if self.direct_abstract_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                if self.direct_abstract_declarator_suffix(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                    nodes.append(tree.pop())

            tree.append((NODE_ABSTRACT_DECLARATOR, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif self.direct_abstract_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] in '[(' and self.direct_abstract_declarator_suffix(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

            tree.append((NODE_ABSTRACT_DECLARATOR, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def direct_abstract_declarator(self, tokIter, tree, info, indent=''):
        '''
	    : '[' ']'",
	    | '[' '*' ']'",
        | '(' abstract_declarator ')'",
	    | '[' assignment_expression ']'",
	    | '(' ')'",
	    | '(' parameter_list ')'",

        First Set:
        '[', '('
        '''
        logger.debug('%s%s' % (indent, 'direct_abstract_declarator'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '[':
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == ']':
                nodes.append(tokIter.getToken())
            elif token[TOK_VALUE] == '*':
                nodes.append(tokIter.getToken())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            elif self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            else:
                logger.debug('%s%s' % (indent, False))
                return False
        elif token[TOK_VALUE] == '(':
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == ')':
                nodes.append(tokIter.getToken())
            elif self.parameter_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            elif self.abstract_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            else:
                logger.debug('%s%s' % (indent, False))
                return False
        else:
            logger.debug('%s%s' % (indent, False))
            return False

        tree.append((NODE_DIRECT_ABSTRACT_DECLARATOR, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def direct_abstract_declarator_suffix(self, tokIter, tree, info, indent=''):
        '''
	    : ( '[' ']'",
	      | '[' assignment_expression ']'",
	      | '[' '*' ']'",
	      | '(' ')'",
	      | '(' parameter_list ')'", )+

        First Set:
        '[', '('
        '''
        logger.debug('%s%s' % (indent, 'direct_abstract_declarator_suffix'))
        nodes = deque()
        while True:
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == '[':
                nodes.append(tokIter.getToken())
                token = tokIter.lookaheadToken(1)
                if token[TOK_VALUE] == ']':
                    nodes.append(tokIter.getToken())
                elif token[TOK_VALUE] == '*':
                    nodes.append(tokIter.getToken())
                    token = tokIter.getToken()
                    assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                    nodes.append(token)
                elif self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                    nodes.append(tree.pop())
                    token = tokIter.getToken()
                    assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                    nodes.append(token)
                else:
                    break
            elif token[TOK_VALUE] == '(':
                nodes.append(tokIter.getToken())
                token = tokIter.lookaheadToken(1)
                if token[TOK_VALUE] == ')':
                    nodes.append(tokIter.getToken())
                elif self.parameter_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                    nodes.append(tree.pop())
                    token = tokIter.getToken()
                    assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                    nodes.append(token)
                else:
                    break
            else:
                break

        if nodes:
            tree.append((NODE_DIRECT_ABSTRACT_DECLARATOR_SUFFIX, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def pointer(self, tokIter, tree, info, indent=''):
        '''
        : ('*' (type_qualifier_list)?)+

        First Set:
        '*'
        '''
        logger.debug('%s%s' % (indent, 'pointer'))
        nodes = deque()
        while True:
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] != '*':
                break

            logger.debug('%s%s' % (indent, str(token)))
            nodes.append(tokIter.getToken())

            if self.type_qualifier_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

        if nodes:
            tree.append((NODE_POINTER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def type_qualifier_list(self, tokIter, tree, info, indent=''):
        '''
        : (type_qualifier)+

        First Set:
        CONST, RESTRICT, VOLATILE
        '''
        logger.debug('%s%s' % (indent, 'type_qualifier_list'))
        nodes = deque()
        while self.type_qualifier(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        if nodes:
            tree.append((NODE_TYPE_QUALIFIER_LIST, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def constant_expression(self, tokIter, tree, info, indent=''):
        '''
        : binary_expression ('?' expression ':' constant_expression)?

        First Set:
        '(', 
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '''
        logger.debug('%s%s' % (indent, 'constant_expression'))
        if not self.binary_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '?':
            nodes.append(tokIter.getToken())

            assert self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse constant_expression @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ':', "expected ':' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse constant_expression @ %s' % info['path']
            nodes.append(tree.pop())

        tree.append((NODE_CONSTANT_EXPRESSION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def binary_expression(self, tokIter, tree, info, indent=''):
        '''
        : cast_expression (('||'|'&&'|'|'|'^'|'&'|'=='|'!='|'<'|'>'|'<='|'>='|'<<'|'>>'|'+'|'-'|'*'|'/'|'%') cast_expression)*

        First Set:
        '(', 
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '''
        logger.debug('%s%s' % (indent, 'binary_expression'))
        if not self.cast_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())
        token = tokIter.lookaheadToken(1)
        while token[TOK_TYPE] == TOK_OPERATOR and token[TOK_VALUE] in '||&&^!==<=>=<<>>+-*/%':
            nodes.append(tokIter.getToken())

            assert self.cast_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse binary_expression @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.lookaheadToken(1)

        tree.append((NODE_BINARY_EXPRESSION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def cast_expression(self, tokIter, tree, info, indent=''):
        '''
        : (cast)* unary_expression

        First Set:
        '(', 
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '''
        logger.debug('%s%s' % (indent, 'cast_expression'))
        nodes = deque()

        #print tree
        if tree and tree[-1][NODE_TYPE] == NODE_UNARY_EXPRESSION:
            nodes.append(tree.pop())
            tree.append((NODE_CAST_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True

        if tree and tree[-1][NODE_TYPE] == NODE_CAST:
            nodes.append(tree.pop())

        while self.cast(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        if self.unary_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_CAST_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def cast(self, tokIter, tree, info, indent=''):
        '''
        : '(' type_name ')'

        First Set:
        '(', 
        '''
        logger.debug('%s%s' % (indent, 'cast'))

        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '(':
            token = tokIter.lookaheadToken(2)
            if token[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC) or (token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types):
                nodes.append(tokIter.getToken())
                assert self.type_name(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse cast_expression @ %s' % info['path']
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
                tree.append((NODE_CAST, nodes))
                logger.debug('%s%s' % (indent, True))
                return True
            else:
                logger.debug('%s%s' % (indent, False))
                return False
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def unary_expression(self, tokIter, tree, info, indent=''):
        '''
        : ('&'|'*'|'+'|'-'|'~'|'!') cast_expression
        : ('++'|'--') unary_expression
        | SIZEOF ('(' type_name ')' | unary_expression)
        | postfix_expression (postfix_expression_suffix)?

        First Set:
        '&'|'*'|'+'|'-'|'~'|'!',
        '++'|'--',
        SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '''
        logger.debug('%s%s' % (indent, 'unary_expression'))
        nodes = deque()

        if tree and tree[-1][NODE_TYPE] == NODE_POSTFIX_EXPRESSION:
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] in '.++-->[(' and self.postfix_expression_suffix(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            tree.append((NODE_UNARY_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent,True))
            return True

        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] in '&*+-~!':
            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(tokIter.getToken())
            assert self.cast_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse unary_expression @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_UNARY_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        elif token[TOK_VALUE] in '++--':
            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(tokIter.getToken())
            assert self.unary_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse unary_expression @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_UNARY_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        elif token[TOK_TYPE] == TOK_SIZEOF:
            logger.debug('%s%s' % (indent, str(token)))
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)
            token2 = tokIter.lookaheadToken(2)
            if token[TOK_VALUE] == '(' and \
                    (token2[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC) or (token2[TOK_TYPE] == TOK_IDENTIFIER and token2[TOK_VALUE] in self.types)):
                nodes.append(tokIter.getToken())
                assert self.type_name(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse unary_expression @ %s' % info['path']
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
                tree.append((NODE_UNARY_EXPRESSION, nodes))
                logger.debug('%s%s' % (indent,True))
                return True
            elif self.unary_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                tree.append((NODE_UNARY_EXPRESSION, nodes))
                logger.debug('%s%s' % (indent,True))
                return True
            else:
                raise Exception("failed to parse unary_expression @ %s" % info['path'])
        elif (tree or token[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC|TOK_CONSTANT|TOK_IDENTIFIER) or token[TOK_VALUE] == '(') and \
                self.postfix_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] in '.++-->[(' and self.postfix_expression_suffix(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            tree.append((NODE_UNARY_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        else:
            logger.debug('%s%s' % (indent,False))
            return False

    def type_name(self, tokIter, tree, info, indent=''):
        '''
        : specifier_qualifier_list (abstract_declarator)?

        First Set:
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION,
        ENUM 
        IDENTIFIER (TYPE_NAME)
        CONST, RESTRICT, VOLATILE

        CONST <= token <= TOK_ENUM, IDENTIFIER
        '''
        logger.debug('%s%s' % (indent, 'type_name'))

        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC|TOK_IDENTIFIER) and \
                self.specifier_qualifier_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] in '*[(' and \
                    self.abstract_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

            tree.append((NODE_TYPE_NAME, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        else:
            logger.debug('%s%s' % (indent,False))
            return False

    def postfix_expression(self, tokIter, tree, info, indent=''):
        '''
        : NUMBER
        | CHARACTER
        | (STRING)+
        | IDENTIFIER
        | type_name   # this is for __builtin_va_arg(ap, type)
        | '(' expression ')'
        | cast initializer_block

        First Set:
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '''
        logger.debug('%s%s' % (indent, 'postfix_expression'))
        nodes = deque()
        if tree and tree[-1][NODE_TYPE] == NODE_CAST:
            nodes.append(tree.pop())

            assert self.initializer_block(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse postfix_expression @ %s' % info['path']
            nodes.append(tree.pop())

            tree.append((NODE_POSTFIX_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent,True))
            return True

        token = tokIter.lookaheadToken(1)
        if (token[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC) or (token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types)) and \
                self.type_name(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
        elif token[TOK_TYPE] == TOK_STRING:
            while token[TOK_TYPE] == TOK_STRING:
                logger.debug('%s%s' % (indent,str(token)))
                nodes.append(tokIter.getToken())
                token = tokIter.lookaheadToken(1)
        elif token[TOK_TYPE] & (TOK_CONSTANT|TOK_IDENTIFIER):
            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(tokIter.getToken())
        elif token[TOK_VALUE] == '(':
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)
            if (token[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC) or (token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types)) and \
                    self.type_name(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)

                if self.initializer_block(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                    nodes.append(tree.pop())
                else:
                    tree.append((NODE_CAST, nodes))
                    logger.debug('%s%s' % (indent,False))
                    return False
            elif self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            else:
                logger.debug('%s%s' % (indent,False))
                return False
        else:
            logger.debug('%s%s' % (indent,False))
            return False

        tree.append((NODE_POSTFIX_EXPRESSION, nodes))
        logger.debug('%s%s' % (indent,True))
        return True

    def initializer_block(self, tokIter, tree, info, indent=''):
        '''
        : '{' initializer_list (',')? '}'

        First Set:
        '{'
        '''
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] != '{':
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tokIter.getToken())

        assert self.initializer_list(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse initializer_block @ %s' % info['path']
        nodes.append(tree.pop())

        token = tokIter.getToken()
        if token[TOK_VALUE] == ',':
            nodes.append(token)
            token = tokIter.getToken()
        assert token[TOK_VALUE] == '}', "expected '}' but got %s @ %s" % (str(token), info['path'])
        nodes.append(token)

        tree.append((NODE_INITIALIZER_BLOCK, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def postfix_expression_suffix(self, tokIter, tree, info, indent=''):
        '''
        : '->' IDENTIFIER
        | '.' IDENTIFIER
        | '++'
        | '--'
        | '[' expression ']'
        | '(' (expression)? ')'

        First Set:
        '->', '.', '++', '--', '[', '('
        '''
        logger.debug('%s%s' % (indent, 'postfix_expression_suffix'))

        nodes = deque()
        while True:
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == '->' or token[TOK_VALUE] == '.':
                nodes.append(tokIter.getToken())
                token = tokIter.getToken()
                assert token[TOK_TYPE] == TOK_IDENTIFIER, "expected IDENTIFIER but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            elif token[TOK_VALUE] == '[':
                nodes.append(tokIter.getToken())
                assert self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse postfix_expression_suffix @ %s" % info['path']
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            elif token[TOK_VALUE] == '(':
                nodes.append(tokIter.getToken())
                if self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                    nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            elif token[TOK_VALUE] == '++' or token[TOK_VALUE] == '--':
                nodes.append(tokIter.getToken())
            else:
                break

        if nodes:
            tree.append((NODE_POSTFIX_EXPRESSION_SUFFIX, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def expression(self, tokIter, tree, info, indent=''):
        '''
        : assignment_expression (',' assignment_expression)*
        | compound_statement	# C extension

        First Set:
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '{'
        '''
        logger.debug('%s%s' % (indent, 'expression'))
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '{' and self.compound_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes = deque()
            nodes.append(tree.pop())
            tree.append((NODE_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif not self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())
        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] == ',':
            logger.debug('%s%s' % (indent, str(token)))
            nodes.append(tokIter.getToken())
            assert self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse expression @ %s" % info['path']
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)

        tree.append((NODE_EXPRESSION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def assignment_expression(self, tokIter, tree, info, indent=''):
        '''
        : (unary_expression ASSIGN_OP)* constant_expression

        First Set:
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('

        unary_expression:
        : ('&'|'*'|'+'|'-'|'~'|'!') cast_expression
        : ('++'|'--') unary_expression
        | SIZEOF ('(' type_name ')' | unary_expression)
        | postfix_expression (postfix_expression_suffix)?

        postfix_expression:
        : NUMBER
        | CHARACTER
        | STRING
        | IDENTIFIER
        | type_name   # this is for __builtin_va_arg(ap, type)
        | '(' expression ')'
        | cast initializer_block

        constant_expression:
        : binary_expression ('?' expression ':' constant_expression)?
        : cast_expression (('||'|'&&'|'|'|'^'|'&'|'=='|'!='|'<'|'>'|'<='|'>='|'<<'|'>>'|'+'|'-'|'*'|'/'|'%') cast_expression)*
        : (cast)* unary_expression
        '''
        logger.debug('%s%s' % (indent, 'assignment_expression'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '(':
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)
            if (token[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC) or (token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types)) and \
                    self.type_name(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
                tree.append((NODE_CAST, nodes))

                nodes = deque()
                token = tokIter.lookaheadToken(1)
                if token[TOK_VALUE] != '{':
                    assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse assignment_expression @ %s" % info['path']
                    nodes.append(tree.pop())
                    tree.append((NODE_ASSIGNMENT_EXPRESSION, nodes))
                    logger.debug('%s%s' % (indent, True))
                    return True
            elif self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
                tree.append((NODE_POSTFIX_EXPRESSION, nodes))
                nodes = deque()
            else:
                raise Exception('failed to parse assignment_expression @ %s' % info['path'])

        while self.unary_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            token = tokIter.lookaheadToken(1)
            if token[TOK_TYPE] == TOK_ASSIGN_OP:
                logger.debug('%s%s' % (indent, str(token)))
                nodes.append(tree.pop())
                nodes.append(tokIter.getToken())
            else:
                break

        if self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_ASSIGNMENT_EXPRESSION, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def init_declarator_list(self, tokIter, tree, info, indent=''):
        '''
        : init_declarator (',' init_declarator)*

        First Set:
        '*', IDENTIFIER, '('

        Follow Set:
        ';'
        '''
        logger.debug('%s%s' % (indent, 'init_declarator_list'))
        if not self.init_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())
        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] == ',':
            nodes.append(tokIter.getToken())
            assert self.init_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse init_declarator_list @ %s" % info['path']
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)

        tree.append((NODE_INIT_DECLARATOR_LIST, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def init_declarator(self, tokIter, tree, info, indent=''):
        '''
        : declarator ('=' initializer)?

        First Set:
        '*', IDENTIFIER, '('
        '''
        logger.debug('%s%s' % (indent, 'init_declarator'))
        nodes = deque()

        if tree and tree[0][NODE_TYPE] == NODE_DECLARATOR:
            nodes.append(tree.popleft())
        elif self.declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
        else:
            logger.debug('%s%s' % (indent, False))
            return False

        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '=':
            nodes.append(tokIter.getToken())
            assert self.initializer(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse init_declarator @ %s" % info['path']
            nodes.append(tree.pop())

        tree.append((NODE_INIT_DECLARATOR, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def initializer(self, tokIter, tree, info, indent=''):
        '''
        : '{' initializer_list '}'
        | assignment_expression

        First Set:
        '{', 
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '''
        logger.debug('%s%s' % (indent, 'initializer'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '{':
            nodes.append(tokIter.getToken())

            assert self.initializer_list(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse initializer @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == '}', "expected '}' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            tree.append((NODE_INITIALIZER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_INITIALIZER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def initializer_list(self, tokIter, tree, info, indent=''):
        '''
        : (designation)? initializer (',' (designation)? initializer)* (',')?

        First Set:
        '[', '.'
        '{', 
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        '''
        logger.debug('%s%s' % (indent, 'initializer_list'))
        nodes = deque()
        if self.designation(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        if not self.initializer(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes.append(tree.pop())
        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] == ',':
            nodes.append(tokIter.getToken())

            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] in '[.' and self.designation(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            elif token[TOK_VALUE] == '}':
                break

            assert self.initializer(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse initializer_list @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.lookaheadToken(1)

        tree.append((NODE_INITIALIZER_LIST, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def labeled_statement(self, tokIter, tree, info, indent=''):
        '''
        : (IDENTIFIER|DEFAULT) ':' statement
        | CASE constant_expression ('...' constant_expression)? ':' statement # C extension (Case Range)

        First Set:
        IDENTIFIER, DEFAULT, CASE
        '''
        logger.debug('%s%s' % (indent, 'labeled_statement'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_TYPE] == TOK_IDENTIFIER or token[TOK_TYPE] == TOK_DEFAULT:
            token = tokIter.lookaheadToken(2)
            if token[TOK_VALUE] == ':':
                nodes.append(tokIter.getToken())
                nodes.append(tokIter.getToken())

                assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse labeled_statement @ %s" % info['path']
                nodes.append(tree.pop())

                tree.append((NODE_LABELED_STATEMENT, nodes))
                logger.debug('%s%s' % (indent, True))
                return True
        elif token[TOK_TYPE] == TOK_CASE:
            nodes.append(tokIter.getToken())

            assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse labeled_statement @ %s" % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            if token[TOK_TYPE] == TOK_ELLIPSIS:
                nodes.append(token)
                assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse labeled_statement @ %s" % info['path']
                token = tokIter.getToken()

            assert token[TOK_VALUE] == ':', "expected ':' or '...' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), "failed to parse labeled_statement @ %s" % info['path']
            nodes.append(tree.pop())

            tree.append((NODE_LABELED_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def compound_statement(self, tokIter, tree, info, indent=''):
        '''
        : '{' (block_item_list)? '}'

        First Set:
        '{'
        '''
        logger.debug('%s%s' % (indent, 'compound_statement'))
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] != '{':
            logger.debug('%s%s' % (indent, False))
            return False

        logger.debug('%s%s' % (indent, str(token)))
        nodes = deque()
        nodes.append(tokIter.getToken())

        if self.block_item_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        token = tokIter.getToken()
        assert token[TOK_VALUE] == '}', "expected '}' but got %s @ %s" % (str(token), info['path'])
        logger.debug('%s%s' % (indent, str(token)))
        nodes.append(token)

        tree.append((NODE_COMPOUND_STATEMENT, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def block_item_list(self, tokIter, tree, info, indent=''):
        '''
        : (block_item)+

        First Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER
        INLINE
        CONST, RESTRICT, VOLATILE
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION, ENUM 
        IDENTIFIER (TYPE_NAME)
        IDENTIFIER, DEFAULT, CASE
        '{'
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        IF, SWITCH
        WHILE, DO, FOR
        GOTO, CONTINUE, BREAK, RETURN
        '''
        logger.debug('%s%s' % (indent, 'block_item_list'))
        nodes = deque()
        while self.block_item(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            #logger.debug('%s%s' % (indent, node))
            nodes.append(tree.pop())

        if nodes:
            tree.append((NODE_BLOCK_ITEM_LIST, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def block_item(self, tokIter, tree, info, indent=''):
        '''
        : declaration
        | statement

        First Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER
        INLINE
        CONST, RESTRICT, VOLATILE
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION, ENUM 
        IDENTIFIER (TYPE_NAME)
        IDENTIFIER, DEFAULT, CASE
        '{'
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        IF, SWITCH
        WHILE, DO, FOR
        GOTO, CONTINUE, BREAK, RETURN
        '''
        logger.debug('%s%s' % (indent, 'block_item'))
        nodes = deque()
        tok = tokIter.lookaheadToken(1)
        logger.debug('%s%s' % (indent, str(tok)))
        if (tok[TOK_TYPE] & (TOK_STORAGE_CLASS|TOK_FUNC_SPEC|TOK_TYPE_QUAL|TOK_TYPE_SPEC) or \
                (tok[TOK_TYPE] == TOK_IDENTIFIER and tok[TOK_VALUE] in self.types)) and \
                self.declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_BLOCK_ITEM, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif (tok[TOK_TYPE] & (TOK_CONSTANT|TOK_IDENTIFIER|TOK_STATEMENT|TOK_SIZEOF) or (tok[TOK_TYPE] == TOK_OPERATOR and tok[TOK_VALUE] in '{(;&*~!++--')) and \
                self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_BLOCK_ITEM, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def statement(self, tokIter, tree, info, indent=''):
        '''
        : labeled_statement
        | compound_statement
        | expression_statement
        | selection_statement
        | iteration_statement
        | jump_statement

        First Set:
        IDENTIFIER, DEFAULT, CASE
        '{'
        OPERATOR, SIZEOF, 
        IDENTIFIER, CHARACTER, NUMBER, STRING, '('
        IF, SWITCH
        WHILE, DO, FOR
        GOTO, CONTINUE, BREAK, RETURN
        '''
        logger.debug('%s%s' % (indent, 'statement'))
        nodes = deque()
        tok = tokIter.lookaheadToken(1)
        if (tok[TOK_TYPE] == TOK_IDENTIFIER or TOK_CASE <= tok[TOK_TYPE] <= TOK_DEFAULT) and \
                self.labeled_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            #logger.debug('%s%s' % (indent, st))
            tree.append((NODE_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif TOK_SWITCH <= tok[TOK_TYPE] <= TOK_IF and \
                self.selection_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            #logger.debug('%s%s' % (indent, st))
            tree.append((NODE_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif TOK_FOR <= tok[TOK_TYPE] <= TOK_WHILE and \
                self.iteration_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            #logger.debug('%s%s' % (indent, st))
            tree.append((NODE_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif TOK_GOTO <= tok[TOK_TYPE] <= TOK_RETURN and \
                self.jump_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            #logger.debug('%s%s' % (indent, st))
            tree.append((NODE_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif tok[TOK_VALUE] == '{' and \
                self.compound_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            #logger.debug('%s%s' % (indent, st))
            tree.append((NODE_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif (tok[TOK_TYPE] & (TOK_CONSTANT|TOK_IDENTIFIER|TOK_SIZEOF) or (tok[TOK_TYPE] == TOK_OPERATOR and tok[TOK_VALUE] in '(&*~!++--;')) and \
                self.expression_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            #logger.debug('%s%s' % (indent, st))
            tree.append((NODE_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def expression_statement(self, tokIter, tree, info, indent=''):
        '''
        : (expression)? ';'

        First Set:
        OPERATOR, SIZEOF, 
        NUMBER, CHARACTER, STRING, IDENTIFIER
        '(', ';'
        '''
        logger.debug('%s%s' % (indent, 'expression_statement'))
        nodes = deque()
        if self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == ';':
                nodes.append(tokIter.getToken())
                tree.append((NODE_EXPRESSION_STATEMENT, nodes))
                logger.debug('%s%s' % (indent, True))
                return True
            else:
                logger.debug('%s%s' % (indent, False))
                return False
        else:
            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == ';':
                nodes.append(tokIter.getToken())
                tree.append((NODE_EXPRESSION_STATEMENT, nodes))
                logger.debug('%s%s' % (indent, True))
                return True
            else:
                logger.debug('%s%s' % (indent, False))
                return False

    def selection_statement(self, tokIter, tree, info, indent=''):
        '''
        : IF '(' expression ')' statement (ELSE statement)?
        | SWITCH '(' expression ')' statement

        First Set:
        IF, SWITCH
        '''
        logger.debug('%s%s' % (indent, 'selection_statement'))
        token = tokIter.lookaheadToken(1)
        nodes = deque()

        if token[TOK_TYPE] == TOK_IF:
            logger.debug('%s%s' % (indent, str(token)))
            nodes.append(tokIter.getToken())

            token = tokIter.getToken()
            logger.debug('%s%s' % (indent, str(token)))
            assert token[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse selection_statement @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
            logger.debug('%s%s' % (indent, str(token)))
            nodes.append(token)

            assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse selection_statement @ %s' % info['path']
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)

            if token[TOK_TYPE] == TOK_ELSE:
                nodes.append(tokIter.getToken())

                assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse selection_statement @ %s' % info['path']
                nodes.append(tree.pop())

            tree.append((NODE_SELECTION_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_SWITCH:
            nodes.append(tokIter.getToken())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse selection_statement @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse selection_statement @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_SELECTION_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def iteration_statement(self, tokIter, tree, info, indent=''):
        '''
        : WHILE '(' expression ')' statement
        | DO statement WHILE '(' expression ')' ';'
        | FOR '(' (expression_statement | declaration) expression_statement (expression)? ')' statement

        First Set:
        WHILE, DO, FOR
        '''
        logger.debug('%s%s' % (indent, 'iteration_statement'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_TYPE] == TOK_WHILE:
            nodes.append(tokIter.getToken())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse iteration_statement @ %s' % info['path'] 
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse iteration_statement @ %s' % info['path'] 
            nodes.append(tree.pop())
            tree.append((NODE_ITERATION_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_DO:
            nodes.append(tokIter.getToken())

            assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse iteration_statement @ %s' % info['path'] 
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_TYPE] == TOK_WHILE, "expected WHILE but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            token = tokIter.getToken()
            assert token[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse iteration_statement @ %s' % info['path'] 
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ';', "expected ';' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            tree.append((NODE_ITERATION_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_FOR:
            nodes.append(tokIter.getToken())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            if self.expression_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            elif self.declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            else:
                raise Exception('failed to parse iteration_statement @ %s' % info['path'])

            assert self.expression_statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse iteration_statement @ %s' % info['path'] 
            nodes.append(tree.pop())

            if self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            assert self.statement(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse iteration_statement @ %s' % info['path'] 
            nodes.append(tree.pop())

            tree.append((NODE_ITERATION_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def jump_statement(self, tokIter, tree, info, indent=''):
        '''
        : GOTO IDENTIFIER ';'
        | (CONTINUE|BREAK) ';'
        | RETURN (expression)? ';'

        First Set:
        GOTO, CONTINUE, BREAK, RETURN
        '''
        logger.debug('%s%s' % (indent, 'jump_statement'))
        token = tokIter.lookaheadToken(1)
        nodes = deque()

        if token[TOK_TYPE] == TOK_GOTO:
            nodes.append(tokIter.getToken())
            logger.debug('%s%s' % (indent, str(token)))

            token = tokIter.getToken()
            assert token[TOK_TYPE] == TOK_IDENTIFIER, "expected IDENTIFIER but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ';', "expected ';' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            tree.append((NODE_JUMP_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_CONTINUE or token[TOK_TYPE] == TOK_BREAK:
            nodes.append(tokIter.getToken())
            logger.debug('%s%s' % (indent, str(token)))

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ';', "expected ';' but got %s @ %s" % (str(token), info['path'])

            tree.append((NODE_JUMP_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_RETURN:
            nodes.append(tokIter.getToken())
            logger.debug('%s%s' % (indent, str(token)))

            if self.expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ';', "expected ';' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            tree.append((NODE_JUMP_STATEMENT, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def declaration_list(self, tokIter, tree, info, indent=''):
        '''
        : (declartion)+
        
        First Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER
        INLINE
        CONST, RESTRICT, VOLATILE
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION, ENUM 
        IDENTIFIER (TYPE_NAME)

        Follow Set:
        '{'
        '''
        logger.debug('%s%s' % (indent, 'declaration_list'))
        nodes = deque()

        while self.declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        if nodes:
            tree.append((NODE_DECLARATION_LIST, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def declartion(self, tokIter, tree, info, indent=''):
        '''
        : declaration_specifiers (init_declarator_list)? ';'

        First Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER
        INLINE
        CONST, RESTRICT, VOLATILE
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION, ENUM 
        IDENTIFIER (TYPE_NAME)
        '''
        logger.debug('%s%s' % (indent, 'declaration'))
        if not self.declaration_specifiers(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())

        if self.init_declarator_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        token = tokIter.getToken()
        assert token[TOK_VALUE] == ';', "expected ';' but got %s @ %s" % (str(token), info['path'])
        nodes.append(token)

        tree.append((NODE_DECLARATION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def function_specifier(self, tokIter, tree, info, indent=''):
        '''
        : INLINE

        First Set:
        INLINE
        '''
        logger.debug('%s%s' % (indent, 'function_specifier'))
        token = tokIter.lookaheadToken(1)

        if token[TOK_TYPE] == TOK_INLINE:
            nodes = deque()
            nodes.append(tokIter.getToken())
            tree.append((NODE_FUNCTION_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def storage_class_specifier(self, tokIter, tree, info, indent=''):
        '''
        : TYPEDEF
        | EXTERN
        | STATIC
        | AUTO
        | REGISTER

        First Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER
        '''
        logger.debug('%s%s' % (indent, 'storage_class_specifier'))
        token = tokIter.lookaheadToken(1)

        if token[TOK_TYPE] & TOK_STORAGE_CLASS:
            logger.debug('%s%s' % (indent,str(token)))
            nodes = deque()
            nodes.append(tokIter.getToken())
            tree.append((NODE_STORAGE_CLASS_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def type_specifier(self, tokIter, tree, info, indent=''):
        '''
        : VOID
        | CHAR
        | SHORT
        | INT
        | LONG
        | FLOAT
        | DOUBLE
        | SIGNED
        | UNSIGNED
        | BOOL
        | COMPLEX
        | IMAGINARY
        | TYPEOF '(' (unary_expression|type_name) ')' # GNU C extension
        | struct_or_union_specifier
        | enum_specifier
        | TYPE_NAME

        First Set:
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION,
        ENUM 
        IDENTIFIER (TYPE_NAME)
        '''
        logger.debug('%s%s' % (indent, 'type_specifier'))
        token = tokIter.lookaheadToken(1)
        logger.debug('%s%s' % (indent,str(token)))
        nodes = deque()

        if TOK_VOID <= token[TOK_TYPE] <= TOK_IMAGINARY:
            nodes.append(tokIter.getToken())
            tree.append((NODE_TYPE_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif TOK_STRUCT <= token[TOK_TYPE] <= TOK_UNION and \
                self.struct_or_union_specifier(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_TYPE_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_ENUM and self.enum_specifier(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            tree.append((NODE_TYPE_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_TYPEOF:
            nodes.append(tokIter.getToken())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            if (token[TOK_TYPE] & (TOK_TYPE_QUAL|TOK_TYPE_SPEC) or (token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types)) and \
                    self.type_name(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            elif self.unary_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            else:
                raise Exception('failed to parse type_specifier @ %s' % info['path'])

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            tree.append((NODE_TYPE_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types:
            nodes.append(tokIter.getToken())
            tree.append((NODE_TYPE_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def struct_or_union_specifier(self, tokIter, tree, info, indent=''):
        '''
        : (STRUCT|UNION) IDENTIFIER ('{' (struct_declaration_list)? '}')?   # C extension (empty decl list)
        | (STRUCT|UNION) '{' (struct_declaration_list)? '}'                 # C extension (empty decl list)

        First Set:
        STRUCT, UNION
        '''
        logger.debug('%s%s' % (indent, 'struct_or_union_specifier'))
        token = tokIter.lookaheadToken(1)

        if token[TOK_TYPE] != TOK_STRUCT and token[TOK_TYPE] != TOK_UNION:
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tokIter.getToken())
        token = tokIter.getToken()

        if token[TOK_TYPE] == TOK_IDENTIFIER:
            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(token)

            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == '{':
                nodes.append(tokIter.getToken())

                if self.struct_declaration_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                    nodes.append(tree.pop())

                token = tokIter.getToken()
                assert token[TOK_VALUE] == '}', "expected '}' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
        else:
            logger.debug('%s%s' % (indent, str(token)))
            assert token[TOK_VALUE] == '{', "expected '{' but oot %s @ %s" % (token, info['path'])
            nodes.append(token)

            assert self.struct_declaration_list(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse struct_or_union_specifier @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == '}', "expected '}' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

        tree.append((NODE_STRUCT_OR_UNION_SPECIFIER, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def struct_declaration_list(self, tokIter, tree, info, indent=''):
        '''
        : (struct_declaration)+

        First Set:
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION,
        ENUM 
        IDENTIFIER (TYPE_NAME)
        CONST, RESTRICT, VOLATILE
        '''
        logger.debug('%s%s' % (indent, 'struct_declaration_list'))
        nodes = deque()

        while self.struct_declaration(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        if nodes:
            tree.append((NODE_STRUCT_DECLARATION_LIST, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def struct_declaration(self, tokIter, tree, info, indent=''):
        '''
        : specifier_qualifier_list (struct_declarator_list)? ';'

        First Set:
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION,
        ENUM 
        IDENTIFIER (TYPE_NAME)
        CONST, RESTRICT, VOLATILE

        CONST <= token <= TOK_ENUM, IDENTIFIER
        '''
        logger.debug('%s%s' % (indent, 'struct_declaration'))

        if not self.specifier_qualifier_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())

        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == ';':
            nodes.append(tokIter.getToken())
        else:
            assert self.struct_declarator_list(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse struct_declaration @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ';', "expected ';' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

        tree.append((NODE_STRUCT_DECLARATION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def specifier_qualifier_list(self, tokIter, tree, info, indent=''):
        '''
        : (type_specifier|type_qualifier)+

        First Set:
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY
        STRUCT, UNION,
        ENUM 
        IDENTIFIER (TYPE_NAME)
        CONST, RESTRICT, VOLATILE

        CONST <= token <= TOK_ENUM, IDENTIFIER
        '''
        logger.debug('%s%s' % (indent, 'specifier_qualifier_list'))
        nodes = deque()

        while True:
            token = tokIter.lookaheadToken(1)
            logger.debug('%s%s' % (indent, str(token)))
            if (token[TOK_TYPE] & TOK_TYPE_SPEC or (token[TOK_TYPE] == TOK_IDENTIFIER and token[TOK_VALUE] in self.types)) and \
                    self.type_specifier(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            elif token[TOK_TYPE] & TOK_TYPE_QUAL  and \
                    self.type_qualifier(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            else:
                #if token[TOK_TYPE] == TOK_IDENTIFIER:
                #    print token
                #    print self.types.has_key(token[TOK_VALUE])
                #    print self.types
                break

        if nodes:
            tree.append((NODE_SPECIFIER_QUALIFIER_LIST, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def struct_declarator_list(self, tokIter, tree, info, indent=''):
        '''
        : struct_declarator (',' struct_declarator)*

        First Set:
        ':',
        '*', IDENTIFIER, '('
        '''
        logger.debug('%s%s' % (indent, 'struct_declarator_list'))

        if not self.struct_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent,False))
            return False

        nodes = deque()
        nodes.append(tree.pop())

        token = tokIter.lookaheadToken(1)

        while token[TOK_VALUE] == ',':
            nodes.append(tokIter.getToken())

            assert self.struct_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse struct_declaration_list @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.lookaheadToken(1)

        tree.append((NODE_STRUCT_DECLARATOR_LIST, nodes))
        logger.debug('%s%s' % (indent,True))
        return True

    def struct_declarator(self, tokIter, tree, info, indent=''):
        '''
        : ':' constant_expression 
        | declarator (':' constant_expression)?

        First Set:
        ':',
        '*', IDENTIFIER, '('
        '''
        logger.debug('%s%s' % (indent, 'struct_declarator'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)

        if token[TOK_VALUE] == ':':
            nodes.append(tokIter.getToken())
            logger.debug('%s%s' % (indent,str(token)))
            assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse constant_expression @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_STRUCT_DECLARATOR, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        elif self.declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] == ':':
                nodes.append(tokIter.getToken())
                logger.debug('%s%s' % (indent,str(token)))
                assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse constant_expression @ %s' % info['path']
                nodes.append(tree.pop())

            tree.append((NODE_STRUCT_DECLARATOR, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        else:
            logger.debug('%s%s' % (indent,False))
            return False

    def declarator(self, tokIter, tree, info, indent=''):
        '''
        : (pointer)? direct_declarator (direct_declarator_suffix)?
        | pointer (direct_declarator (direct_declarator_suffix)?)?

        First Set:
        '*', IDENTIFIER, '('

        Follow Set:
        TYPEDEF, EXTERN, STATIC, AUTO, REGISTER,
        INLINE,
        CONST, RESTRICT, VOLATILE,
        VOID, CHAR, SHORT, INT, LONG, FLOAT, DOUBLE, SIGNED, UNSIGNED, BOOL, COMPLEX, IMAGINARY,
        STRUCT, UNION, ENUM,
        IDENTIFIER (TYPE_NAME),
        '{', '=', ':' , ')'
        '''
        logger.debug('%s%s' % (indent, 'declarator'))

        nodes = deque()
        token = tokIter.lookaheadToken(1)

        if token[TOK_VALUE] == '*' and self.pointer(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

        if self.direct_declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())

            token = tokIter.lookaheadToken(1)
            if token[TOK_VALUE] in '[(' and self.direct_declarator_suffix(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

        if nodes:
            tree.append((NODE_DECLARATOR, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        else:
            logger.debug('%s%s' % (indent,False))
            return False

    def direct_declarator(self, tokIter, tree, info, indent=''):
        '''
        : IDENTIFIER
        | '(' declarator ')'

        First Set:
        IDENTIFIER, '('
        '''
        logger.debug('%s%s' % (indent, 'direct_declarator'))

        nodes = deque()
        token = tokIter.lookaheadToken(1)

        if token[TOK_TYPE] == TOK_IDENTIFIER:
            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(tokIter.getToken())
            tree.append((NODE_DIRECT_DECLARATOR, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        elif token[TOK_VALUE] == '(':
            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(tokIter.getToken())

            if self.declarator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
            else:
                logger.error('failed to parse direct_declarator @ %s' % info['path'])

            token = tokIter.getToken()
            logger.debug('%s%s' % (indent,str(token)))
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            tree.append((NODE_DIRECT_DECLARATOR, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        else:
            logger.debug('%s%s' % (indent,str(token)))
            logger.debug('%s%s' % (indent,False))
            return False

    def direct_declarator_suffix(self, tokIter, tree, info, indent=''):
        '''
        #: (parameter_specifier|dimension_specifier)+
        : parameter_specifier
        | (dimension_specifier)+

        First Set:
        '[', '('
        '''
        logger.debug('%s%s' % (indent, 'direct_declarator_suffix'))

        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '(':
            assert self.parameter_specifier(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse direct_declarator_suffix @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_DIRECT_DECLARATOR_SUFFIX, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        elif token[TOK_VALUE] == '[':
            while True:
                assert self.dimension_specifier(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse direct_declarator_suffix @ %s' % info['path']
                nodes.append(tree.pop())
                token = tokIter.lookaheadToken(1)
                if token[TOK_VALUE] != '[':
                    break
            tree.append((NODE_DIRECT_DECLARATOR_SUFFIX, nodes))
            logger.debug('%s%s' % (indent,True))
            return True
        else:
            logger.debug('%s%s' % (indent,False))
            return False

    def parameter_specifier(self, tokIter, tree, info, indent=''):
        '''
        : '(' ')'
        | '(' parameter_list ')'
        | '(' identifier_list ')'
        '''
        logger.debug('%s%s' % (indent, 'parameter_specifier'))
        token = tokIter.lookaheadToken(1)

        if token[TOK_VALUE] == '(':
            logger.debug('%s%s' % (indent, str(token)))
            nodes = deque()
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)

            if token[TOK_VALUE] == ')':
                logger.debug('%s%s' % (indent, str(token)))
                nodes.append(tokIter.getToken())
            elif self.parameter_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            elif self.identifier_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
            else:
                raise Exception('failed to parse parameter_specifier @ %s' % info['path'])

            tree.append((NODE_PARAMETER_SPECIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def dimension_specifier(self, tokIter, tree, info, indent=''):
        '''
        : '[' ']'
        | '[' '*' ']'
        | '[' STATIC type_qualifier_list assignment_expression ']'
        | '[' assignment_expression ']'
        | '[' type_qualifier_list ']'
        | '[' type_qualifier_list '*' ']'
        | '[' type_qualifier_list STATIC assignment_expression ']'
        | '[' type_qualifier_list assignment_expression ']'
        '''
        logger.debug('%s%s' % (indent, 'dimension_specifier'))
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] != '[':
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        logger.debug('%s%s' % (indent, str(token)))
        nodes.append(tokIter.getToken())
        token = tokIter.lookaheadToken(1)

        if token[TOK_VALUE] == ']':
            logger.debug('%s%s' % (indent, str(token)))
            nodes.append(tokIter.getToken())
        elif token[TOK_VALUE] == '*':
            nodes.append(tokIter.getToken())
            token = tokIter.getToken()
            assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)
            logger.debug('%s%s' % (indent, str(token)))
        elif token[TOK_TYPE] == TOK_STATIC:
            nodes.append(tokIter.getToken())

            assert self.type_qualifier_list(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse direct_declarator @ %s' % info['path']
            nodes.append(tree.pop())

            assert self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse direct_declarator @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)
            logger.debug('%s%s' % (indent, str(token)))
        elif self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            token = tokIter.getToken()
            assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)
            logger.debug('%s%s' % (indent, str(token)))
        elif self.type_qualifier_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
            token = tokIter.lookaheadToken(1)

            if token[TOK_VALUE] == ']':
                nodes.append(tokIter.getToken())
                logger.debug('%s%s' % (indent, str(token)))
            elif token[TOK_VALUE] == '*':
                nodes.append(tokIter.getToken())
                token = tokIter.getToken()
                assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
                logger.debug('%s%s' % (indent, str(token)))
            elif token[TOK_TYPE] == TOK_STATIC:
                nodes.append(tokIter.getToken())

                assert self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse direct_declarator @ %s' % info['path']
                nodes.append(tree.pop())

                token = tokIter.getToken()
                assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
                logger.debug('%s%s' % (indent, str(token)))
            elif self.assignment_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())

                token = tokIter.getToken()
                assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)
                logger.debug('%s%s' % (indent, str(token)))
            else:
                raise Exception('failed to parse dimension_specifier @ %s' % info['path'])
        else:
            raise Exception('failed to parse dimension_specifier @ %s' % info['path'])

        tree.append((NODE_DIMENSION_SPECIFIER, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def identifier_list(self, tokIter, tree, info, indent=''):
        '''
        : IDENTIFIER (',' IDENTIFIER)*

        First Set:
        IDENTIFIER
        '''
        logger.debug('%s%s' % (indent, 'identifier_list'))

        token = tokIter.lookaheadToken(1)
        if token[TOK_TYPE] != TOK_IDENTIFIER:
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tokIter.getToken())

        logger.debug('%s%s' % (indent,str(token)))
        token = tokIter.lookaheadToken(1)

        while token[TOK_VALUE] == ',':
            nodes.append(tokIter.getToken())

            token = tokIter.getToken()
            assert token[TOK_TYPE] == TOK_IDENTIFIER, 'expected IDENTIFIER but got %s' % str(token)

            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(token)
            token = tokIter.lookaheadToken(1)

        tree.append((NODE_IDENTIFIER_LIST, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def enum_specifier(self, tokIter, tree, info, indent=''):
        '''
        : ENUM '{' enumerator_list '}'
        | ENUM IDENTIFIER ('{' enumerator_list '}')?

        First Set:
        ENUM
        '''
        logger.debug('%s%s' % (indent, 'enum_specifer'))

        token = tokIter.lookaheadToken(1)
        if token[TOK_TYPE] != TOK_ENUM:
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tokIter.getToken())

        token = tokIter.lookaheadToken(1)

        if token[TOK_TYPE] == TOK_IDENTIFIER:
            nodes.append(tokIter.getToken())
            token = tokIter.lookaheadToken(1)

            if token[TOK_VALUE] == '{':
                nodes.append(tokIter.getToken())

                assert self.enumerator_list(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse enum_specifer @ %s' % info['path']
                nodes.append(tree.pop())

                token = tokIter.getToken()
                assert token[TOK_VALUE] == '}', "expected '}' but got %s @ %s" % (str(token), info['path'])
                nodes.append(token)

                tree.append((NODE_ENUM_SPECIFIER, nodes))
            else:
                tree.append((NODE_ENUM_SPECIFIER, nodes))
        else:
            assert token[TOK_VALUE] == '{', "expected '{' but got %s @ %s" % (str(token), info['path'])
            nodes.append(tokIter.getToken())

            assert self.enumerator_list(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse enum_specifer @ %s' % info['path']
            nodes.append(tree.pop())

            token = tokIter.getToken()
            if token[TOK_VALUE] == ',':
                nodes.append(token)
                token = tokIter.getToken()

            assert token[TOK_VALUE] == '}', "expected '}' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)

            tree.append((NODE_ENUM_SPECIFIER, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def enumerator_list(self, tokIter, tree, info, indent=''):
        '''
        : enumerator (',' enumerator)* (',')?

        First Set:
        IDENTIFIER
        '''
        logger.debug('%s%s' % (indent, 'enumerator_list'))
        if not self.enumerator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False

        nodes = deque()
        nodes.append(tree.pop())

        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] == ',':
            nodes.append(tokIter.getToken())

            token = tokIter.lookaheadToken(1)
            if token[TOK_TYPE] == TOK_IDENTIFIER and self.enumerator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
                nodes.append(tree.pop())
                token = tokIter.lookaheadToken(1)
            else:
                break

        tree.append((NODE_ENUMERATOR_LIST, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def enumerator(self, tokIter, tree, info, indent=''):
        '''
        : IDENTIFIER ('=' constant_expression)?

        First Set:
        IDENTIFIER
        '''
        logger.debug('%s%s' % (indent, 'enumerator'))

        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_TYPE] != TOK_IDENTIFIER:
            logger.debug('%s%s' % (indent, False))
            return False

        token = tokIter.getToken()
        logger.debug('%s%s' % (indent, str(token)))
        nodes.append(token)

        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '=':
            nodes.append(tokIter.getToken())
            logger.debug('%s%s' % (indent, str(token)))
            assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse constant_expression @ %s' % info['path']
            nodes.append(tree.pop())
            tree.append((NODE_ENUMERATOR, nodes))
        else:
            tree.append((NODE_ENUMERATOR, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def type_qualifier(self, tokIter, tree, info, indent=''):
        '''
        : CONST
        | RESTRICT
        | VOLATILE

        First Set:
        CONST, RESTRICT, VOLATILE
        '''
        logger.debug('%s%s' % (indent, 'type_qualifier'))
        token = tokIter.lookaheadToken(1)
        if token[TOK_TYPE] & TOK_TYPE_QUAL:
            logger.debug('%s%s' % (indent,str(token)))
            nodes = deque()
            nodes.append(tokIter.getToken())
            tree.append((NODE_TYPE_QUALIFIER, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def designation(self, tokIter, tree, info, indent=''):
        '''
        : designator_list '='

        First Set:
        '[', '.'
        '''
        logger.debug('%s%s' % (indent, 'designation'))
        if not self.designator_list(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            logger.debug('%s%s' % (indent, False))
            return False
        nodes = deque()
        nodes.append(tree.pop())
        token = tokIter.getToken()
        assert token[TOK_VALUE] == '=', "expected '=' but got %s @ %s" % (str(token), info['path'])
        nodes.append(token)
        tree.append((NODE_DESIGNATION, nodes))
        logger.debug('%s%s' % (indent, True))
        return True

    def designator_list(self, tokIter, tree, info, indent=''):
        '''
        : (designator)+

        First Set:
        '[', '.'
        '''
        logger.debug('%s%s' % (indent, 'designator_list'))
        nodes = deque()
        while self.designator(tokIter, tree, info, '%s%s'%(indent,INDENT)):
            nodes.append(tree.pop())
        if nodes:
            tree.append((NODE_DESIGNATOR_LIST, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

    def designator(self, tokIter, tree, info, indent=''):
        '''
        : '[' constant_expression ']'
        | '.' IDENTIFIER

        First Set:
        '[', '.'
        '''
        logger.debug('%s%s' % (indent, 'designator'))
        nodes = deque()
        token = tokIter.lookaheadToken(1)
        if token[TOK_VALUE] == '[':
            nodes.append(tokIter.getToken())
            assert self.constant_expression(tokIter, tree, info, '%s%s'%(indent,INDENT)), 'failed to parse designator @ %s' % info['path']
            nodes.append(tree.pop())
            token = tokIter.getToken()
            assert token[TOK_VALUE] == ']', "expected ']' but got %s @ %s" % (str(token), info['path'])
            nodes.append(token)
            tree.append((NODE_DESIGNATOR, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        elif token[TOK_VALUE] == '.':
            nodes.append(tokIter.getToken())
            token = tokIter.getToken()
            assert token[TOK_TYPE] == TOK_IDENTIFIER, "expected IDENTIFIER but got %s @ %s" % (str(token), info['path'])
            logger.debug('%s%s' % (indent,str(token)))
            nodes.append(token)
            tree.append((NODE_DESIGNATOR, nodes))
            logger.debug('%s%s' % (indent, True))
            return True
        else:
            logger.debug('%s%s' % (indent, False))
            return False

