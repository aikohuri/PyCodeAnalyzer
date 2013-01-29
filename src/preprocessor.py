from collections import deque, defaultdict
import os
import logging
from distutils import dir_util
import subprocess

from scanner import Scanner
from scanner_types import *
from token_iter import TokenIterator


logger = logging.getLogger('cpp')
logger.setLevel(logging.INFO)

# create console handler and set level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(funcName)-22s:%(lineno)4d:%(message)s'))
logger.addHandler(ch)

INDENT='  '


class Preprocessor:
    global logger

    tokenTbl = defaultdict(deque)
    predefMacroDefs = defaultdict(deque)
    predefMacroKeys = defaultdict(deque) 
    sysIncDirs = None
    appIncDirs = None
    predefMacros = None

    @staticmethod
    def getPredefMacros():
        predefMacros = {}

        s = subprocess.Popen(['-c', 'cpp -E -dM - < /dev/null'], stdout=subprocess.PIPE, shell=True)
        for line in [l for l in s.communicate()[0].split('\n') if l]:
            words = line.split(' ')
            predefMacros[words[1]] = ' '.join(words[2:])
        predefMacros['__extension__'] = ''
        predefMacros['__attribute__(x)'] = ''
        predefMacros['__signed__'] = ''
        predefMacros['__inline'] = 'inline'
        predefMacros['__volatile__'] = 'volatile'
        predefMacros['__restrict'] = 'restrict'
        predefMacros['__const'] = 'const'
        predefMacros['__typeof__'] = 'typeof'
        predefMacros['__typeof'] = 'typeof'
        predefMacros['__format__(...)'] = ''
        predefMacros['__nonnull(...)'] = ''
        predefMacros['__asm__(...)'] = ''
        predefMacros['__BEGIN_NAMESPACE_STD'] = ''
        predefMacros['__END_NAMESPACE_STD'] = ''
        predefMacros['__USING_NAMESPACE_STD(x)'] = ''

        return predefMacros

    @staticmethod
    def getDefaultIncDirs():
        sysIncDirs = []
        appIncDirs = []

        cppIncSpecFName = os.path.expanduser('~/.cpp_inc_search_path')
        os.system('cpp -v < /dev/null > %s 2>&1' % (cppIncSpecFName))
        f = open(cppIncSpecFName, 'rb')
        lines = f.readlines()
        f.close()
        sysFound = False
        appFound = False

        for line in lines:
            if line.startswith('#include "..."'):
                appFound = True
            elif line.startswith('#include <...>'):
                sysFound = True
                appFound = False
            elif line.startswith('End of search list'):
                break
            elif appFound:
                appIncDirs.append(line.strip())
            elif sysFound:
                sysIncDirs.append(line.strip())

        print '#include "..." search dir:\n', '\n'.join(['\t%s' % d for d in appIncDirs])
        print '#include <...> search dir:\n', '\n'.join(['\t%s' % d for d in sysIncDirs])

        return sysIncDirs, appIncDirs

    @classmethod
    def clearTokenCache(cls):
        cls.tokenTbl.clear()

    @classmethod
    def getIncDirs(cls):
        if cls.sysIncDirs is None and cls.appIncDirs is None:
            cls.sysIncDirs, cls.appIncDirs = cls.getDefaultIncDirs()
        return cls.sysIncDirs, cls.appIncDirs

    @classmethod
    def setIncDirs(cls, sysIncDirs, appIncDirs):
        cls.sysIncDirs = sysIncDirs
        cls.appIncDirs = appIncDirs

    @classmethod
    def getSysIncDirs(cls):
        if cls.sysIncDirs is None and cls.appIncDirs is None:
            cls.sysIncDirs, cls.appIncDirs = cls.getDefaultIncDirs()
        return self.__class__.sysIncDirs

    @classmethod
    def setSysIncDirs(cls, incDirs):
        cls.sysIncDirs = incDirs

    @classmethod
    def getAppIncDirs(cls):
        if cls.sysIncDirs is None and cls.appIncDirs is None:
            cls.sysIncDirs, cls.appIncDirs = cls.getDefaultIncDirs()
        return cls.appIncDirs

    @classmethod
    def setAppIncDirs(cls, incDirs):
        cls.appIncDirs = incDirs

    def __init__(self, sysIncDirs=None, appIncDirs=None, predefMacros=None, save=False, removeComment=False, outputDir='', expandObjMacro=False, expandFuncMacro=False, externalLogger=None, logLevel=None, logPath=None):
        self.globalMacroDefs = defaultdict(tuple)
        self.globalMacroKeys = defaultdict(deque)
        self.eval_stack = deque()

        self.saveFile = save
        self.removeComment = removeComment
        self.outputDir = outputDir
        self.expandObjMacro = expandObjMacro
        self.expandFuncMacro = expandFuncMacro
        self.expandMacro = self.expandObjMacro or self.expandFuncMacro

        if self.__class__.predefMacros is None:
            self.__class__.predefMacros = self.__class__.getPredefMacros()
        self.predefMacros = predefMacros if predefMacros is not None else self.__class__.predefMacros

        if self.__class__.sysIncDirs is None and self.__class__.appIncDirs:
            self.__class__.sysIncDirs, self.__class__.appIncDirs = self.__class__.getDefaultIncDirs()
        self.sysIncDirs = sysIncDirs if sysIncDirs is not None else self.__class__.sysIncDirs
        self.appIncDirs = appIncDirs if appIncDirs is not None else self.__class__.appIncDirs

        if externalLogger:
            externalLogger.setLevel(logging.INFO)
            externalLogger.setFormatter(logging.Formatter('%(levelname)-7s:%(name)s:%(message)s'))
            logger.addHandler(externalLogger)

        if logLevel:
            logger.setLevel(eval('logging.%s' % logLevel))

        if logPath:
            if os.path.exists(logPath):
                os.remove(logPath)
            # This handler writes everything to a file.
            fh = logging.FileHandler(logPath)
            fh.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(funcName)-22s:%(lineno)4d:%(message)s"))
            fh.setLevel(logging.DEBUG)
            logger.addHandler(fh)
        else:
            # This handler writes everything to a file.
            fh = logging.FileHandler("/var/log/preprocessor.log")
            fh.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(funcName)-22s:%(lineno)4d:%(message)s"))
            fh.setLevel(logging.DEBUG)
            logger.addHandler(fh)

    def preprocess_predef(self):
        predefInfo = {
            'path'      : 'predefined',
            'defines'   : deque(),
            'macroCalls': deque(),
        }

        scanner = Scanner()
        for name, val in self.__class__.predefMacros.items():
            scanner.setString('%s %s' % (name, val))
            self.define_directive(scanner, predefInfo)

        self.__class__.predefMacroKeys.update(self.globalMacroKeys)
        self.__class__.predefMacroDefs.update(self.globalMacroDefs)

        ppInfo = {
            'path'      : 'predefined',
            'defines'   : predefInfo['defines'],
            'macroCalls': predefInfo['macroCalls'],
            'tokens'    : deque(),
            'undefs'    : deque(),
            'includes'  : deque(),
        }

        return ppInfo

    def preprocess(self, path):
        logger.info('preprocess %s' % path)

        self.eval_stack.clear()
        self.globalMacroKeys.clear()
        self.globalMacroDefs.clear()

        self.globalMacroKeys.update(self.__class__.predefMacroKeys)
        self.globalMacroDefs.update(self.__class__.predefMacroDefs)
        return self._preprocess(path, None)

    def _preprocess(self, curPath, parents, indent=''):
        logger.info('%s_preprocess %s' % (indent, curPath))

        #oldcwd = os.getcwd()
        cwd = os.path.split(curPath)[0]
        #os.chdir(cwd)
        #logger.debug('%schdir %s' % (indent, cwd))

        if not self.__class__.tokenTbl.has_key(curPath):
            self.__class__.tokenTbl[curPath] = Scanner(curPath).tokenize()

        tokIter = TokenIterator(self.__class__.tokenTbl[curPath])

        outTokens = deque()
        saveTokens = None if not self.saveFile else deque()

        ppInfo = {'path': curPath,
                  'cwd': cwd,
                  'parents': parents if parents else deque(),
                  'tokens': outTokens,
                  'saveTokens': saveTokens,
                  'defines': deque(),
                  'macroCalls': deque(),
                  'undefs': deque(),
                  'includes': deque(),
                  'pragmas': deque(),
                  }

        getToken = tokIter.getToken
        appendSave = None if saveTokens is None else saveTokens.append
        appendOut = outTokens.append
        extendOut = outTokens.extend
        token = getToken()

        while token:
            if token[TOK_TYPE] & TOK_OPERATOR and token[TOK_VALUE] == '#':
                if saveTokens is not None: appendSave(token)
                self.directives(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            elif token[TOK_TYPE] == TOK_IDENTIFIER:
                if saveTokens is not None and not self.expandMacro: appendSave(token)
                ident = self.identifier(token, tokIter, ppInfo, '%s%s'%(indent,INDENT))
                if ident == token:
                    appendOut(ident)
                    if saveTokens is not None and self.expandMacro: appendSave(ident)
                else:
                    if saveTokens is not None and self.expandMacro: appendSave((token[TOK_TYPE], ' '.join([t[TOK_VALUE] for t in ident if t]), token[TOK_ROW], token[TOK_COL]))
                    if outTokens and outTokens[-1][TOK_TYPE] == TOK_STRING:
                        tok = outTokens.pop()
                        val = tok[TOK_VALUE].strip('"')
                        while ident:
                            t = ident.popleft()
                            if t[TOK_TYPE] == TOK_STRING:
                                val = '%s%s' % (val, t[TOK_VALUE].strip('"'))
                            else:
                                break
                        token = (tok[TOK_TYPE], '"%s"' % val, tok[TOK_ROW], tok[TOK_COL])
                        appendOut(token)
                        extendOut(ident)
                    else:
                        extendOut(ident)
            elif token[TOK_TYPE] != TOK_COMMENT:
                if saveTokens is not None: appendSave(token)
                if token[TOK_VALUE] != '\\':
                    if token[TOK_TYPE] == TOK_STRING and outTokens and outTokens[-1][TOK_TYPE] == TOK_STRING:
                        tok = outTokens.pop()
                        token = (tok[TOK_TYPE],
                                 '"%s%s"' % (tok[TOK_VALUE].strip('"'), token[TOK_VALUE].strip('"')),
                                 tok[TOK_ROW],
                                 tok[TOK_COL])
                        appendOut(token)
                    else:
                        appendOut(token)
            elif saveTokens is not None and not self.removeComment:
                appendSave(token)

            token = getToken()

        if saveTokens is not None:
            self.save_tokens(self.outputDir, ppInfo, '%s%s'%(indent,INDENT))

        #os.chdir(oldcwd)
        #logger.debug('%schdir %s' % (indent, oldcwd))

        del ppInfo['cwd']
        del ppInfo['saveTokens']

        return ppInfo

    def directives(self, tokIter, ppInfo, indent=''):
        '''
        directive
            : define_directive
            | include_directive
            | include_next_directive
            | endif_directive
            | if_directive
            | elif_directive
            | ifdef_directive
            | ifndef_directive
            | else_directive
            | endif_directive
            | undef_directive
            | error_directive
            | warning_directive
            | ident_directive
            | line_directive
            | pragma_directive
        '''
        saveTokens = None if not self.saveFile else ppInfo['saveTokens']
        token = tokIter.getToken()
        if token[TOK_TYPE] == TOK_PP_DEFINE:
            if saveTokens is not None: saveTokens.append(token)
            self.define_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_INCLUDE:
            if saveTokens is not None: saveTokens.append(token)
            self.include_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_ENDIF:
            if saveTokens is not None: saveTokens.pop()
            self.endif_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_IF:
            if saveTokens is not None: saveTokens.pop()
            self.if_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_ELIF:
            if saveTokens is not None: saveTokens.pop()
            self.elif_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_IFDEF:
            if saveTokens is not None: saveTokens.pop()
            self.ifdef_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_IFNDEF:
            if saveTokens is not None: saveTokens.pop()
            self.ifndef_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_ELSE:
            if saveTokens is not None: saveTokens.pop()
            self.else_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_UNDEF:
            if saveTokens is not None: saveTokens.append(token)
            self.undef_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_INCLUDE_NEXT:
            if saveTokens is not None: saveTokens.append(token)
            self.include_next_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_ERROR:
            if saveTokens is not None: saveTokens.pop()
            self.error_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_WARNING:
            if saveTokens is not None: saveTokens.pop()
            self.warning_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_IDENT:
            if saveTokens is not None: saveTokens.append(token)
            self.ident_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_LINE:
            if saveTokens is not None: saveTokens.append(token)
            self.line_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_TYPE] == TOK_PP_PRAGMA:
            if saveTokens is not None: saveTokens.append(token)
            self.pragma_directive(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        else:
            raise Exception('unknown directive %s %s' % (str(token), ppInfo['path']))

    def include_directive(self, tokIter, ppInfo, indent=''):
        '''
        include_directive
            : '#' include (STRING | '<' path_specifier '>')
        '''
        saveTokens = None if not self.saveFile else ppInfo['saveTokens']
        token = tokIter.getToken()
        pos = token[TOK_ROW:]

        if saveTokens is not None: saveTokens.append(token)

        if token[TOK_TYPE] == TOK_STRING:
            path = token[TOK_VALUE]
        elif token[TOK_VALUE] == '<':
            path = '<%s>' % self.path_specifier(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            token = tokIter.getToken()
            if saveTokens is not None: saveTokens.append(token)
            assert token[TOK_VALUE] == '>', "expected '>' but got %s @ %s" % (str(token), ppInfo['path'])
        else:
            raise Exception('*** invalid token after include directive %s ***' % str(token))

        logger.debug('%s#include %s %s' % (indent, path, pos))
        abspath = self.search_file(path, ppInfo, '', '%s%s'%(indent,INDENT))
        logger.debug('%s%s' % (indent, abspath))
        if abspath:
            parents = ppInfo['parents']
            parents.append(ppInfo['path'])
            info = self._preprocess(abspath, parents, '%s%s'%(indent,INDENT))
            parents.pop()
            logger.debug('%sdone with %s ... continue on %s' % (indent, abspath, ppInfo['path']))
        else:
            info = None
            logger.error('*** %s not found @ %s %s***' % (path, pos, ppInfo['path']))
        ppInfo['includes'].append((path, abspath, pos, info))

    def include_next_directive(self, tokIter, ppInfo, indent=''):
        '''
        include_directive
            : '#' include (STRING | '<' path_specifier '>')
        '''
        saveTokens = None if not self.saveFile else ppInfo['saveTokens']

        token = tokIter.getToken()
        pos = token[TOK_ROW:]
        if saveTokens is not None: saveTokens.append(token)

        if token[TOK_TYPE] == TOK_STRING:
            path = token[TOK_VALUE]
        elif token[TOK_VALUE] == '<':
            path = '<%s>' % self.path_specifier(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            token = tokIter.getToken()
            if saveTokens is not None: saveTokens.append(token)
        else:
            raise Exception('*** invalid token after include directive %s ***' % str(token))

        logger.debug('%s#include_next %s %s' % (indent, path, pos))
        abspath = self.search_file(path, ppInfo, ppInfo['cwd'])
        logger.debug('%s%s' % (indent, abspath))
        if abspath:
            parents = ppInfo['parents']
            parents.append(ppInfo['path'])
            info = self._preprocess(abspath, parents, '%s%s'%(indent,INDENT))
            parents.pop()
            logger.debug('%sdone with %s ... continue on %s' % (indent, abspath, ppInfo['path']))
        else:
            info = None
            logger.error('*** %s not found @ %s %s ***' % (path, pos, ppInfo['path']))
        ppInfo['includes'].append((path, abspath, pos, info))

    def define_directive(self, tokIter, ppInfo, indent=''):
        '''
        define_directive
            : '#' define IDENTIFIER['(' [parameter_list] ')'] [macro_value]
        '''
        saveTokens = None if not self.saveFile else ppInfo.get('saveTokens', None)
        getToken = tokIter.getToken
        appendSave = None if saveTokens is None else saveTokens.append
        identTok = getToken()
        if saveTokens is not None: appendSave(identTok)

        logger.debug('%s%s' % (indent, str(identTok)))
        assert identTok[TOK_TYPE] == TOK_IDENTIFIER, 'invalid IDENTIFIER %s for #define' % str(identTok)

        token = tokIter.lookaheadToken(1)
        if token and token[TOK_VALUE] == '(' and token[TOK_COL] == identTok[TOK_COL] + len(identTok[TOK_VALUE]):
            token = getToken()
            if saveTokens is not None: appendSave(token)
            assert token[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(token), ppInfo['path'])

            params = self.parameter_list(tokIter, ppInfo, '%s%s'%(indent,INDENT))

            token = getToken()
            if saveTokens is not None: appendSave(token)
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), ppInfo['path'])

            token = tokIter.lookaheadToken(1)
        else:
            params = None

        value = deque()
        appendValue = value.append
        ln = identTok[TOK_ROW]
        while token and token[TOK_ROW] == ln:
            token = getToken()
            if token[TOK_TYPE] != TOK_COMMENT:
                if saveTokens is not None: appendSave(token)
                appendValue(token)
            elif saveTokens is not None and not self.removeComment:
                appendSave(token)

            if token[TOK_VALUE] == '\\':
                ln += 1

            token = tokIter.lookaheadToken(1)

        name = identTok[TOK_VALUE]
        pos  = identTok[TOK_ROW:]
        logger.debug('%smacro: %s(%s) %s %s' % (indent, name,
                                               None if params is None else ', '.join([p[TOK_VALUE] for p in params if p]),
                                               ''.join([v[TOK_VALUE] for v in value if v]),
                                               pos))

        key = (name, ppInfo['path'], pos)
        self.globalMacroKeys[name].append(key)
        self.globalMacroDefs[key] = (params, value)

        expandedValue = self.expand_object_macro(identTok, self.globalMacroDefs[key], ppInfo, '%s%s'%(indent,INDENT))
        ppInfo['defines'].append((name,
                                  None if params is None else deque([p[TOK_VALUE] for p in params if p]), 
                                  ' '.join([v[TOK_VALUE] for v in value if v]),
                                  ' '.join([v[TOK_VALUE] for v in expandedValue if v]),
                                  pos))
        logger.debug('%s%s' % (indent, str(ppInfo['defines'][-1])))

    def undef_directive(self, tokIter, ppInfo, indent=''):
        '''
        undef_directive
            : '#' undef IDENTIFIER
        '''
        saveTokens = None if not self.saveFile else ppInfo['saveTokens']

        token = tokIter.getToken()
        if saveTokens is not None: saveTokens.append(token)
        logger.debug('%s%s' % (indent, str(token)))
        assert token[TOK_TYPE] == TOK_IDENTIFIER, 'invalid IDENTIFIER %s for #define' % str(token)

        macroName = token[TOK_VALUE]
        ppInfo['undefs'].append((macroName, token[TOK_ROW:]))

        if self.globalMacroKeys.get(macroName, None):
            ppInfo['macroCalls'].append((macroName, token[TOK_ROW:]))
            del self.globalMacroKeys[macroName]

    def line_directive(self, tokIter, ppInfo, indent=''):
        '''
        line_directive
            : '#' line NUMBER STRING
        '''
        saveTokens = None if not self.saveFile else ppInfo['saveTokens']
        tokenLn = tokIter.getToken()
        if saveTokens is not None: saveTokens.append(tokenLn)
        assert tokenLn[TOK_TYPE] == TOK_NUMBER, 'expected NUMBER but got %s' % str(tokenLn)
        tokenStr = tokIter.getToken()
        if saveTokens is not None: saveTokens.append(tokenStr)
        assert tokenStr[TOK_TYPE] == TOK_STRING, 'expected STRING but got %s' % str(tokenStr)
        logger.debug('%s#line %s %s %s' % (indent, tokenLn[TOK_VALUE],tokenStr[TOK_VALUE], tokenLn[TOK_ROW:]))

    def if_directive(self, tokIter, ppInfo, indent=''):
        '''
        if_directive
            : '#' if conditional_expression
        '''
        tokens = tokIter.getLineTokens()
        while tokens[-1][TOK_VALUE] == '\\':
            tokens.extend(tokIter.getLineTokens())

        if len(tokens) == 1:
            ret = self.unary_expression(TokenIterator(tokens), ppInfo, '%s%s'%(indent,INDENT))
        else:
            ret = self.conditional_expression(TokenIterator(tokens), ppInfo, '%s%s'%(indent,INDENT))

        self.eval_stack.append(ret)
        logger.debug('%s%s' % (indent, str(self.eval_stack)))

        if not ret: self.discard_statements(tokIter, '%s%s'%(indent,INDENT))

    def elif_directive(self, tokIter, ppInfo, indent=''):
        '''
        elif_directive
            : '#' elif conditional_expression
        '''
        if self.eval_stack[-1]:
            self.discard_statements(tokIter, '%s%s'%(indent,INDENT))
        else:
            tokens = tokIter.getLineTokens()
            while tokens[-1][TOK_VALUE] == '\\':
                tokens.extend(tokIter.getLineTokens())

            if len(tokens) == 1:
                ret = self.unary_expression(TokenIterator(tokens), ppInfo, '%s%s'%(indent,INDENT))
            else:
                ret = self.conditional_expression(TokenIterator(tokens), ppInfo, '%s%s'%(indent,INDENT))

            self.eval_stack[-1] = ret
            logger.debug('%s%s' % (indent, str(self.eval_stack)))
            if not ret: self.discard_statements(tokIter, '%s%s'%(indent,INDENT))

    def ifdef_directive(self, tokIter, ppInfo, indent=''):
        '''
        ifdef_directive
            : '#' ifdef IDENTIFIER
        '''

        token = tokIter.getToken()
        logger.debug('%s%s' % (indent, str(token)))
        assert token[TOK_TYPE] == TOK_IDENTIFIER, "expected IDENTIFIER but got %s @ %s" % (str(token), ppInfo['path'])

        ppInfo['macroCalls'].append((token[TOK_VALUE], token[TOK_ROW:]))

        ret = self.globalMacroKeys.has_key(token[TOK_VALUE])
        self.eval_stack.append(ret)
        logger.debug('%s%s' % (indent, str(self.eval_stack)))
        if not ret: self.discard_statements(tokIter, '%s%s'%(indent,INDENT))

    def ifndef_directive(self, tokIter, ppInfo, indent=''):
        '''
        ifndef_directive
            : '#' ifndef IDENTIFIER
        '''
        token = tokIter.getToken()
        logger.debug('%s%s' % (indent, str(token)))
        assert token[TOK_TYPE] == TOK_IDENTIFIER, "expected IDENTIFIER but got %s @ %s" % (str(token), ppInfo['path'])

        ppInfo['macroCalls'].append((token[TOK_VALUE], token[TOK_ROW:]))

        ret = not self.globalMacroKeys.has_key(token[TOK_VALUE])

        self.eval_stack.append(ret)
        logger.debug('%s%s' % (indent, str(self.eval_stack)))
        if not ret: self.discard_statements(tokIter, '%s%s'%(indent,INDENT))

    def else_directive(self, tokIter, ppInfo, indent=''):
        '''
        else_directive
            : '#' else
        '''
        if self.eval_stack[-1]:
            self.discard_statements(tokIter, '%s%s'%(indent,INDENT))

    def endif_directive(self, tokIter, ppInfo, indent=''):
        '''
        endif_directive
            : '#' endif
        '''
        self.eval_stack.pop()
        logger.debug('%s%s' % (indent, str(self.eval_stack)))

    def pragma_directive(self, tokIter, ppInfo, indent=''):
        '''
        pragma_directive
            : '#' pragma tokens
        '''
        tokens = tokIter.getLineTokens()
        while tokens[-1][TOK_VALUE] == '\\':
            tokens.extend(tokIter.getLineTokens())
        if self.saveFile: ppInfo['saveTokens'].extend(tokens)
        pragma = ' '.join([t[TOK_VALUE] for t in tokens if t])
        ppInfo['pragmas'].append((pragma, tokens[0][TOK_ROW:]))
        logger.debug('%s#pragma %s %s' % (indent, pragma, tokens[0][TOK_ROW:]))

    def error_directive(self, tokIter, ppInfo, indent=''):
        '''
        error_directive
            : '#' error tokens
        '''
        tokens = tokIter.getLineTokens()
        while tokens[-1][TOK_VALUE] == '\\':
            tokens.extend(tokIter.getLineTokens())
        logger.error('#error %s @ %s %s' % (
                      ' '.join([t[TOK_VALUE] for t in tokens if t]),
                      str(tokens[0][TOK_ROW:]),
                      ppInfo['path']
                      ))
        raise Exception('#error %s @ %s %s' % (
                        ' '.join([t[TOK_VALUE] for t in tokens if t]),
                        str(tokens[0][TOK_ROW:]),
                        ppInfo['path']
                        ))

    def warning_directive(self, tokIter, ppInfo, indent=''):
        '''
        warning_directive
            : '#' warning tokens
        '''
        tokens = tokIter.getLineTokens()
        while tokens[-1][TOK_VALUE] == '\\':
            tokens.extend(tokIter.getLineTokens())
        logger.warning('#warning %s @ %s %s' % (
                        ' '.join([t[TOK_VALUE] for t in tokens if t]),
                        str(tokens[0][TOK_ROW:]),
                        ppInfo['path']
                        ))
        raw_input()

    def ident_directive(self, tokIter, ppInfo, indent=''):
        '''
        ident_directive
            : '#' ident STRING
        '''
        token = tokIter.getToken()
        if self.saveFile: ppInfo['saveTokens'].append(token)
        assert token[TOK_TYPE] == TOK_STRING, 'expected STRING but got %s' % str(token)
        logger.debug('%s#ident %s' % (indent, token[TOK_VALUE:]))

    def search_file(self, path, ppInfo, offsetDir='', indent=''):
        '''
        search absolute path of included file
        '''
        abspath = ''
        logger.debug('%scurrent working directory: %s' % (indent, ppInfo['cwd']))
        if offsetDir:
            logger.debug('%soffset directory: %s' % (indent, offsetDir))

        if path.startswith('<'):
            #
            # search file in system include directory
            #
            if offsetDir and offsetDir in self.sysIncDirs:
                idx = self.sysIncDirs.index(offsetDir) + 1
            else:
                idx = 0

            for inc in self.sysIncDirs[idx:]:
                logger.debug('%ssearching in %s' % (indent, inc))
                abspath = os.path.join(inc, path[1:-1])
                if os.path.isfile(abspath):
                    break
                else:
                    abspath = ''
        else:
            #
            # search current file directory
            #
            cwd = ppInfo['cwd']
            logger.debug('%ssearching in %s' % (indent, cwd))
            if not offsetDir or cwd != offsetDir:
                abspath = os.path.join(cwd, path[1:-1])
            logger.debug('%s%s%s' % (indent, abspath, os.path.isfile(abspath)))

            if not abspath or not os.path.isfile(abspath):
                #
                # search include directory
                #
                if offsetDir and offsetDir in self.appIncDirs:
                    idx = self.appIncDirs.index(offsetDir) + 1
                else:
                    idx = 0

                for inc in self.appIncDirs[idx:]:
                    logger.debug('%ssearching in %s' % (indent, inc))
                    abspath = os.path.join(inc, path[1:-1])
                    if os.path.isfile(abspath):
                        break
                    else:
                        abspath = ''

        return abspath

    def path_specifier(self, tokIter, ppInfo, indent=''):
        '''
        path_specifier
            : [^>]+
        '''
        saveTokens = None if not self.saveFile else ppInfo['saveTokens']
        path = ''
        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] != '>':
            token = tokIter.getToken()
            if saveTokens is not None: saveTokens.append(token)
            path = '%s%s' % (path, token[TOK_VALUE])
            token = tokIter.lookaheadToken(1)
        return path

    def parameter_list(self, tokIter, ppInfo, indent=''):
        '''
        parameter_list :
            IDENTIFIER (, IDENTIFIER)* (, ELLIPSIS)?
        '''
        saveTokens = None if not self.saveFile else ppInfo.get('saveTokens', None)
        params = deque()
        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] != ')':
            token = tokIter.getToken()
            if token[TOK_TYPE] == TOK_COMMENT:
                if saveTokens is not None and not self.removeComment: saveTokens.append(token)
                token = tokIter.lookaheadToken(1)
            elif token[TOK_VALUE] == '\\':
                if saveTokens is not None: saveTokens.append(token)
                token = tokIter.lookaheadToken(1)
            elif token[TOK_VALUE] != ',':
                if saveTokens is not None: saveTokens.append(token)
                logger.debug('%s%s', indent, str(token))
                params.append(token)
                token = tokIter.lookaheadToken(1)
                if token[TOK_VALUE] == ',':
                    token = tokIter.getToken() # discard ','
                    if saveTokens is not None: saveTokens.append(token)
                    token = tokIter.lookaheadToken(1)
            else:
                if saveTokens is not None: saveTokens.append(token)
                params.append('')
                token = tokIter.lookaheadToken(1)
        return params

    def conditional_expression(self, tokIter, ppInfo, indent=''):
        '''
        : logical_expression ['?' conditional_expression ':' conditional_expression]
        '''
        ret = self.logical_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        token = tokIter.lookaheadToken(1)

        while token and token[TOK_VALUE] == '\\':
            tokIter.getToken()
            token = tokIter.lookaheadToken(1)

        if token and token[TOK_VALUE] == '?':
            token = tokIter.getToken() # discard '?'
            assert token[TOK_VALUE] == '?', "expected '?' but got %s @ %s" % (str(token), ppInfo['path'])
            logger.debug('%s?' % indent)
            true_val = self.conditional_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            token = tokIter.getToken() # discard ':'
            assert token[TOK_VALUE] == ':', "expected ':' but got %s @ %s" % (str(token), ppInfo['path'])
            logger.debug('%s:' % indent)
            false_val = self.conditional_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            ret = true_val if ret else false_val
        logger.debug('%s%s', indent, bool(ret))
        return ret

    def logical_expression(self, tokIter, ppInfo, indent=''):
        '''
        unary_expression {binary_op unary_expression}
        '''
        val1 = self.unary_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        token = tokIter.lookaheadToken(1)

        while token and token[TOK_VALUE] == '\\':
            tokIter.getToken()
            token = tokIter.lookaheadToken(1)

        while token and token[TOK_TYPE] & TOK_OPERATOR and token[TOK_VALUE] in '&&||^==!=<=>=<<>>+-*/%':
            op = tokIter.getToken()[TOK_VALUE]
            if op == '&&':
                op = 'and'
            elif op == '||':
                op = 'or'
            val2 = self.unary_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            logger.debug('%s%d %s %d' % (indent, val1, op, val2))
            val1 = eval('%d %s %d' % (val1, op, val2))
            token = tokIter.lookaheadToken(1)

            while token and token[TOK_VALUE] == '\\':
                tokIter.getToken()
                token = tokIter.lookaheadToken(1)

        return val1

    def unary_expression(self, tokIter, ppInfo, indent=''):
        '''
        unary_expression
            : TOK_NUMBER
            | CHARACTER
            | IDENTIFIER ['(' argument_list ')']
            | defined_operator
            | '(' conditional_expression ')'
            | unary_op unary_expression
        '''
        token = tokIter.getToken()

        while token and token[TOK_VALUE] == '\\':
            token = tokIter.getToken()

        ret = 0
        if token[TOK_TYPE] & TOK_OPERATOR and token[TOK_VALUE] in '+-~!':
            logger.debug('%s%s' % (indent, token[TOK_VALUE]))
            if token[TOK_VALUE] == '!':
                ret = not self.unary_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            else:
                ret = eval('%s %d' % (token[TOK_VALUE], self.unary_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))))
        elif token[TOK_TYPE] == TOK_NUMBER:
            logger.debug('%s%s' % (indent, token[TOK_VALUE]))
            ret = long(token[TOK_VALUE].strip('ulUL'), 0)
        elif token[TOK_TYPE] == TOK_CHARACTER:
            logger.debug('%s%s' % (indent, token[TOK_VALUE]))
            ret = ord(token[TOK_VALUE][-2])
        elif token[TOK_TYPE] == TOK_PP_DEFINED:
            ret = self.defined_operator(tokIter, ppInfo, '%s%s'%(indent,INDENT))
        elif token[TOK_VALUE] == '(':
            logger.debug('%s%s' % (indent, token[TOK_VALUE]))
            ret = self.conditional_expression(tokIter, ppInfo, '%s%s'%(indent,INDENT))
            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), ppInfo['path'])
        elif token[TOK_TYPE] == TOK_IDENTIFIER:
            logger.debug('%s%s' % (indent, str(token)))
            macroName = token[TOK_VALUE]
            macroDef = self.getMacroDef(macroName)
            if macroDef:
                nextTok = tokIter.lookaheadToken(1)
                if macroDef[0] is None:
                    ret = self.evaluate_object_macro(token, macroDef, ppInfo, '%s%s'%(indent,INDENT))
                elif macroDef[0] is not None and nextTok[TOK_VALUE] == '(':
                    nextTok = tokIter.getToken() # discard '('
                    assert nextTok[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(nextTok), ppInfo['path'])
                    logger.debug('%s(' % indent)
                    temp = self.saveFile
                    self.saveFile = False
                    args = self.argument_list(tokIter, ppInfo, '%s%s'%(indent,INDENT))
                    self.saveFile = temp
                    nextTok = tokIter.getToken() # discard ')'
                    assert nextTok[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(nextTok), ppInfo['path'])
                    logger.debug('%s)' % indent)
                    ret = self.evaluate_function_macro(token, macroDef, args, ppInfo, '%s%s'%(indent,INDENT))
        else:
            assert False, 'failed to handle token %s @ %s' % (str(token), ppInfo['path'])

        return ret

    def argument_list(self, tokIter, ppInfo, indent=''):
        '''
        argument_list
            : tokens {',' tokens}
        '''
        saveTokens = None if not self.saveFile or self.expandFuncMacro else ppInfo.get('saveTokens', None)
        args = deque()
        token = tokIter.lookaheadToken(1)
        while token[TOK_VALUE] != ')':
            arg = deque()
            nparen = 0
            while True:
                if token[TOK_VALUE] == ',':
                    if nparen == 0:
                        token = tokIter.getToken()
                        if saveTokens is not None: saveTokens.append(token)
                        token = tokIter.lookaheadToken(1)
                        break
                    else:
                        token = tokIter.getToken()
                        if saveTokens is not None: saveTokens.append(token)
                        arg.append(token)
                elif token[TOK_VALUE] == ')':
                    if nparen == 0:
                        break
                    else:
                        token = tokIter.getToken()
                        if saveTokens is not None: saveTokens.append(token)
                        arg.append(token)
                        nparen -= 1
                elif token[TOK_VALUE] == '(':
                    token = tokIter.getToken()
                    if saveTokens is not None: saveTokens.append(token)
                    arg.append(token)
                    nparen += 1
                elif token[TOK_VALUE] == '\\':
                    token = tokIter.getToken()
                    if saveTokens is not None: saveTokens.append(token)
                elif token[TOK_TYPE] == TOK_COMMENT:
                    token = tokIter.getToken()
                    if saveTokens is not None and not self.removeComment: saveTokens.append(token)
                elif token[TOK_TYPE] == TOK_IDENTIFIER:
                    token = tokIter.getToken()
                    if saveTokens is not None and not self.expandMacro: saveTokens.append(token)
                    ident = self.identifier(token, tokIter, ppInfo, '%s%s'%(indent,INDENT))
                    if ident == token:
                        arg.append(ident)
                        if saveTokens is not None and self.expandMacro: saveTokens.append(ident)
                    else:
                        arg.extend(ident)
                        if saveTokens is not None and self.expandMacro:
                            macroDef = self.getMacroDef(token[TOK_VALUE])
                            if (self.expandObjMacro and macroDef[0] is None) or (self.expandFuncMacro and macroDef[0] is not None):
                                saveTokens.append((token[TOK_TYPE], ' '.join([t[TOK_VALUE] for t in ident if t]), token[TOK_ROW], token[TOK_COL]))
                            else:
                                saveTokens.append(token)
                else:
                    token = tokIter.getToken()
                    arg.append(token)
                    if saveTokens is not None: saveTokens.append(token)
                token = tokIter.lookaheadToken(1)
            logger.debug('%s%s' % (indent, ' '.join([a[TOK_VALUE] for a in arg])))
            args.append(arg)
        return args

    def identifier(self, identTok, tokIter, ppInfo, indent=''):
        '''
        identifier
            : IDENTIFIER ['(' argument_list ')']
        '''
        saveTokens = None if not self.saveFile or self.expandFuncMacro else ppInfo.get('saveTokens', None)
        logger.debug('%s%s' % (indent, str(identTok)))

        macroName = identTok[TOK_VALUE]
        macroDef = self.getMacroDef(macroName)
        if not macroDef:
            return identTok
        else:
            nextTok = tokIter.lookaheadToken(1)
            if macroDef[0] is None:
                ppInfo['macroCalls'].append((macroName, identTok[TOK_ROW:]))
                return self.expand_object_macro(identTok, macroDef, ppInfo, '%s%s'%(indent,INDENT))
            elif macroDef[0] is not None and nextTok and nextTok[TOK_VALUE] == '(':
                ppInfo['macroCalls'].append((macroName, identTok[TOK_ROW:]))
                tok = tokIter.getToken() # discard '('
                if saveTokens is not None: saveTokens.append(tok)
                assert tok[TOK_VALUE] == '(', "expected '(' but got %s @ %s" % (str(tok), ppInfo['path'])
                argList = self.argument_list(tokIter, ppInfo, '%s%s'%(indent,INDENT))
                tok = tokIter.getToken() # discard ')'
                if saveTokens is not None: saveTokens.append(tok)
                assert tok[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(tok), ppInfo['path'])
                return self.expand_function_macro(identTok, macroDef, argList, ppInfo, '%s%s'%(indent,INDENT))
            else:
                return identTok

    def getMacroDef(self, macroName, indent=''):
        keys = self.globalMacroKeys.get(macroName)
        if keys:
            return self.globalMacroDefs[keys[-1]]
        else:
            return None

    def evaluate_object_macro(self, macroNameTok, macroDef, ppInfo, indent=''):
        logger.debug('%s%s' % (indent, str(macroNameTok[TOK_VALUE:])))
        if len(macroDef[1]) == 1:
            return self.unary_expression(TokenIterator(macroDef[1]), ppInfo, '%s%s'%(indent,INDENT))
        else:
            return self.conditional_expression(TokenIterator(macroDef[1]), ppInfo, '%s%s'%(indent,INDENT))

    def evaluate_function_macro(self, macroNameTok, macroDef, args, ppInfo, indent=''):
        logger.debug('%s%s' % (indent, str(macroNameTok)))
        logger.debug('%sparam: %s' % (indent, ', '.join([t[TOK_VALUE] for t in macroDef[0] if t])))
        logger.debug('%sargs : %s' % (indent, ', '.join([''.join([a[TOK_VALUE] for a in arg if a]) for arg in args])))
        #
        # add parameter as macro and set its value to argument
        # in order to replace param name with the argument
        #
        for paramTok, arg in zip(macroDef[0], args):
            if paramTok and paramTok[TOK_TYPE] != TOK_ELLIPSIS:
                key = (paramTok[TOK_VALUE], ppInfo['path'], paramTok[TOK_ROW:])
                self.globalMacroKeys[paramTok[TOK_VALUE]].append(key)
                self.globalMacroDefs[key] = (None, arg)

        if len(macroDef[1]) == 1:
            ret = self.unary_expression(TokenIterator(macroDef[1]), ppInfo, '%s%s'%(indent,INDENT))
        else:
            ret = self.conditional_expression(TokenIterator(macroDef[1]), ppInfo, '%s%s'%(indent,INDENT))

        #
        # delete added parameters
        #
        for paramTok in macroDef[0]:
            if paramTok and paramTok[TOK_TYPE] != TOK_ELLIPSIS:
                del self.globalMacroDefs[self.globalMacroKeys[paramTok[TOK_VALUE]].pop()]

        return ret

    def expand_object_macro(self, macroNameTok, macroDef, ppInfo, indent=''):
        '''
        process '##' and '#' operators.
        removes '\\'.
        expands all macros in the definition
        '''
        logger.debug('%s%s' % (indent, str(macroNameTok)))
        logger.debug('%sbef: %s' % (indent, ' '.join([t[TOK_VALUE] for t in macroDef[1] if t])))

        tokens = TokenIterator(macroDef[1])
        expandedTokens = deque()
        token = tokens.getToken()

        while token:
            if token[TOK_TYPE] == TOK_CONCAT_OP:
                # Concatenation
                ltok = expandedTokens.pop()
                rtok = tokens.getToken()
                logger.debug('%slTok:%s %s rTok:%s' % (indent, ltok[TOK_VALUE], token[TOK_VALUE], rtok[TOK_VALUE]))
                if rtok[TOK_VALUE] == '__VA_ARGS__':
                    #
                    # don't concatenate
                    # http://gcc.gnu.org/onlinedocs/cpp/Variadic-Macros.html
                    #
                    expandedTokens.extend([ltok, token, rtok])
                    token = tokens.getToken()
                    continue
                else:
                    token = (ltok[TOK_TYPE], '%s%s'%(ltok[TOK_VALUE],rtok[TOK_VALUE]), ltok[TOK_ROW], ltok[TOK_COL])
            elif token[TOK_VALUE] == '#':
                # Stringification
                rtok = tokens.getToken()
                token = (TOK_STRING, '"%s"' % rtok[TOK_VALUE], rtok[TOK_ROW], rtok[TOK_COL])
            elif token[TOK_VALUE] == '\\':
                token = tokens.getToken()
                continue

            if token[TOK_TYPE] != TOK_IDENTIFIER or token[TOK_VALUE] == macroNameTok[TOK_VALUE]:
                expandedTokens.append(token)
            else:
                temp = self.saveFile
                self.saveFile = False
                if token[TOK_VALUE] != macroNameTok[TOK_VALUE]:
                    ident = self.identifier(token, tokens, ppInfo, '%s%s'%(indent,INDENT))
                else:
                    print token
                    raw_input()
                    ident = token
                self.saveFile = temp
                if ident == token:
                    expandedTokens.append(ident)
                else:
                    expandedTokens.extend(ident)
            token = tokens.getToken()

        logger.debug('%saft: %s' % (indent, ' '.join([t[TOK_VALUE] for t in expandedTokens if t])))
        return expandedTokens

    def expand_function_macro(self, macroNameTok, macroDef, args, ppInfo, indent=''):
        '''
        process '##' and '#' operators.
        removes '\\'.
        expands all macros in the definition and replace parameters with its arguments
        '''
        logger.debug('%s%s' % (indent, str(macroNameTok)))
        logger.debug('%sparam: %s' % (indent, ', '.join([t[TOK_VALUE] for t in macroDef[0] if t])))
        logger.debug('%sargs : %s' % (indent, ', '.join([''.join([a[TOK_VALUE] for a in arg if a]) for arg in args])))
        logger.debug('%sbef  : %s' % (indent, ' '.join([t[TOK_VALUE] for t in macroDef[1] if t])))

        tbl = defaultdict(tuple)
        for i, (param, arg) in enumerate(zip(macroDef[0], args)):
            if param and param[TOK_TYPE] == TOK_IDENTIFIER:
                tbl[param[TOK_VALUE]] = arg
            elif param and param[TOK_TYPE] == TOK_ELLIPSIS:
                #
                # store the variable argument
                #
                dq = deque()
                prev = None
                for j in range(i, len(args)):
                    if prev:
                        #
                        # need to add ',' between arguements
                        #
                        dq.append((TOK_OPERATOR, ',', prev[TOK_ROW], prev[TOK_COL]+len(prev[TOK_VALUE])))
                    for a in args[j]:
                        prev = a
                        dq.append(a)
                tbl['__VA_ARGS__'] = dq
                break # '...' must be the last parameter

        logger.debug('%sparam vs args: %s' % (indent, str(tbl)))

        tokens = TokenIterator(macroDef[1])
        expandedTokens = deque()
        token = tokens.getToken()

        while token:
            if token[TOK_TYPE] == TOK_CONCAT_OP:
                # Concatenation
                ltok = expandedTokens.pop()
                rtok = tokens.getToken()
                logger.debug('%slTok:%s %s rTok:%s' % (indent, str(ltok), str(token), str(rtok)))
                if rtok[TOK_VALUE] == '__VA_ARGS__':
                    if tbl and tbl.has_key('__VA_ARGS__'):
                        #
                        # delete "##"
                        #
                        expandedTokens.append(ltok)
                        token = rtok
                    else:
                        #
                        # delete ", ## __VA_ARGS__" if the variable argument is left out
                        # http://gcc.gnu.org/onlinedocs/cpp/Variadic-Macros.html
                        #
                        token = tokens.getToken()
                        continue
                else:
                    if not tbl:
                        rtok_val = rtok[TOK_VALUE]
                    else:
                        arg = tbl.get(rtok[TOK_VALUE], None)
                        if not arg:
                            rtok_val = rtok[TOK_VALUE]
                        elif len(arg) == 1:
                            rtok_val = arg[0][TOK_VALUE]
                        else:
                            print arg
                            raw_input('need to fix')
                    token = (TOK_IDENTIFIER, '%s%s'%(ltok[TOK_VALUE],rtok_val), ltok[TOK_ROW], ltok[TOK_COL])
                    logger.debug('%s%s' % (indent, str(token)))
            elif token[TOK_VALUE] == '#':
                # Stringification
                rtok = tokens.getToken()
                logger.debug('%s%s%s' % (indent, str(token), str(rtok)))
                if not tbl:
                    rtok_val = rtok[TOK_VALUE]
                else:
                    arg = tbl.get(rtok[TOK_VALUE], None)
                    if not arg:
                        rtok_val = rtok[TOK_VALUE]
                    elif len(arg) == 1:
                        rtok_val = arg[0][TOK_VALUE]
                    else:
                        print arg
                        raw_input('need to fix')
                token = (TOK_STRING, '"%s"' % rtok_val, rtok[TOK_ROW], rtok[TOK_COL])
                logger.debug('%s%s' % (indent, str(token)))
            elif token[TOK_VALUE] == '\\':
                token = tokens.getToken()
                continue

            if token[TOK_TYPE] != TOK_IDENTIFIER or token[TOK_VALUE] == macroNameTok[TOK_VALUE]:
                expandedTokens.append(token)
            else:
                temp = self.saveFile
                self.saveFile = False
                ident = self.identifier(token, tokens, ppInfo, '%s%s'%(indent,INDENT))
                self.saveFile = temp
                if ident == token:
                    if tbl:
                        arg = tbl.get(token[TOK_VALUE], None)
                        if arg:
                            logger.debug('%s%s' % (indent, 'replace %s with %s' % (str(token), str(arg))))
                            expandedTokens.extend(arg)
                        else:
                            expandedTokens.append(token)
                    else:
                        expandedTokens.append(token)
                else:
                    if tbl:
                        for tok in ident:
                            if tok[TOK_TYPE] != TOK_IDENTIFIER:
                                expandedTokens.append(tok)
                                continue
                            arg = tbl.get(tok[TOK_VALUE], None)
                            if arg:
                                logger.debug('%s%s' % (indent, 'replace %s with %s' % (str(tok), str(arg))))
                                expandedTokens.extend(arg)
                            else:
                                expandedTokens.append(tok)
                    else:
                        expandedTokens.extend(ident)
            token = tokens.getToken()

        logger.debug('%saft: %s' % (indent, ' '.join([t[TOK_VALUE] for t in expandedTokens if t])))
        return expandedTokens

    def defined_operator(self, tokIter, ppInfo, indent=''):
        '''
        defined_expression :
            defined ['('] IDENTIFIER [')']
        '''
        token = tokIter.getToken()

        if token[TOK_TYPE] == TOK_IDENTIFIER:
            logger.debug('%s%s' % (indent, str(token)))
            name = token[TOK_VALUE]
            ppInfo['macroCalls'].append((name, token[TOK_ROW:]))
        elif token[TOK_VALUE] == '(':
            token = tokIter.getToken()
            logger.debug('%s%s' % (indent, str(token)))
            name = token[TOK_VALUE]
            ppInfo['macroCalls'].append((name, token[TOK_ROW:]))
            token = tokIter.getToken()
            assert token[TOK_VALUE] == ')', "expected ')' but got %s @ %s" % (str(token), ppInfo['path'])
        else:
            raise Exception('invalid token after defined operator %s' % token)

        ret = self.globalMacroKeys.has_key(name)
        logger.debug('%s%s' % (indent, bool(ret)))
        return ret

    def discard_statements(self, tokIter, indent=''):
        '''
        discards statements in False clause
        '''
        numIf = 1
        while numIf:
            token = tokIter.lookaheadToken(1)
            if not token:
                break
            elif token[TOK_VALUE] == '#':
                token = tokIter.lookaheadToken(2)
                if token[TOK_TYPE] == TOK_PP_ENDIF:
                    numIf -= 1
                    tokIter.skipLine()
                    if numIf == 0:
                        self.eval_stack.pop()
                        logger.debug('%s%s' % (indent, str(self.eval_stack)))
                elif TOK_PP_IF <= token[TOK_TYPE] <= TOK_PP_IFNDEF:
                    numIf += 1
                    tokIter.skipLine()
                elif TOK_PP_ELIF <= token[TOK_TYPE] <= TOK_PP_ELSE:
                    if numIf == 1:
                        numIf -= 1
                    else:
                        tokIter.skipLine()
                else:
                    tokIter.skipLine()
            else:
                tokIter.skipLine()

    def save_tokens(self, outDir, ppInfo, indent=''):
        parents = ppInfo['parents']
        path = ppInfo['path']

        if parents:
            for p in parents:
                outDir = '%s%s%s' % (outDir, os.path.sep, p[p.rfind(os.path.sep)+1:p.rfind('.')])

        if not os.path.exists(outDir):
            dir_util.mkpath(outDir, verbose=True)

        #path = '%s%s%s' % (outDir, path.replace(os.path.sep, '_'))
        path = '%s%s%s' % (outDir, os.path.sep, path.replace(os.path.sep, '_').strip('_'))

        tokens = ppInfo['saveTokens']
        data = ''
        row = 1
        col = 1

        token = None
        while tokens:
            prev_tok = token
            token = tokens.popleft()
            padding = ''

            if token[TOK_ROW] > row:
                delta = token[TOK_ROW] - row
                padding = '\n' * delta
                row += delta
                col = 1

            if token[TOK_ROW] == row and token[TOK_COL] > col:
                delta = token[TOK_COL] - col
                padding = '%s%s' % (padding, ' ' * delta)
                col += delta

            if not padding and not (token[TOK_TYPE] & TOK_OPERATOR) and prev_tok and not (prev_tok[TOK_TYPE] & TOK_OPERATOR):
                padding = ' '

            data = '%s%s%s' % (data, padding, token[TOK_VALUE])

            if token[TOK_TYPE] == TOK_COMMENT and token[TOK_VALUE].startswith('/*'):
                newlines = token[TOK_VALUE].count('\n')
                if newlines > 0:
                    row += newlines - 1
                    idx = token[TOK_VALUE].rfind('\n')
                    col = len(token[TOK_VALUE][idx+1:])
                else:
                    col += len(token[TOK_VALUE])
            else:
                col += len(token[TOK_VALUE])

        f = open(path, 'w')
        f.write(data)
        f.close()

