from collections import deque

from scanner_types import *


class StringBuffer:

    def __init__(self, iStr):
        self.buffer = iStr

    def readline(self):
        idx = self.buffer.find('\n')
        line = ''
        if idx < 0:
            line = self.buffer
            self.buffer = ''
        else:
            line = self.buffer[:idx+1]
            self.buffer = self.buffer[idx+1:]
        return line

    def close(self):
        pass


class Scanner:

    def __init__(self, iFileName='', iStr=''):
        if iFileName:
            self.fptr = open(iFileName, 'r')
        elif iStr:
            self.fptr = StringBuffer(iStr)
        else:
            self.fptr = None

        self.buf = ''
        self.bufLen = 0
        self.curIdx = -1
        self.row = 0
        self.col = 0
        self.c = ''
        self.curToken = ''
        self.tokenQ = deque()
        self.hashSign = False

    def setFile(self, iFileName):
        self.fptr = open(iFileName, 'r')
        self.buf = ''
        self.bufLen = 0
        self.curIdx = -1
        self.row = 0
        self.col = 0
        self.c = ''
        self.curToken = ''
        self.tokenQ = deque()

    def setString(self, iStr):
        self.fptr = StringBuffer(iStr)
        self.buf = ''
        self.bufLen = 0
        self.curIdx = -1
        self.row = 0
        self.col = 0
        self.c = ''
        self.curToken = ''
        self.tokenQ = deque()

    def lookaheadToken(self, num):
        if num <= 0:
            raise IndexError('lookahead should be > 0')
        size = len(self.tokenQ)
        while num > size:
            self.tokenQ.append(self._getToken())
            size += 1
        return self.tokenQ[num-1]

    def skipLine(self):
        if self.tokenQ:
            self.tokenQ.clear()
        self.buf = ''
        self.bufLen = 0
        self.curIdx = -1

    def getLineTokens(self):
        ret = self.tokenQ
        r = self.row
        token = self._getToken()
        while r == self.row and token:
            ret.append(token)
            token = self._getToken()
        self.tokenQ = deque([token])
        return ret

    def getToken(self):
        if self.tokenQ:
            return self.tokenQ.popleft()
        else:
            return self._getToken()

    def tokenize(self):
        tokens = deque()
        token = self._getToken()
        while token[TOK_TYPE] != TOK_EOF:
            tokens.append(token)
            token = self._getToken()
        return tokens

    def _getNext(self):
        self.col += 1
        self.curIdx += 1

        if self.curIdx < self.bufLen:
            self.c = self.buf[self.curIdx]
        else:
            if self.fptr:
                line = self.fptr.readline()
            else:
                line = ''

            if not line:
                self.c = ''
                if self.fptr:
                    self.fptr.close()
                    self.fptr = None
            else:
                self.buf = '%s%s' % (self.buf, line)
                self.bufLen = len(self.buf)
                self.row += 1
                self.col = 1
                self.c = self.buf[self.curIdx]

        return self.c

    def _lookahead(self, idx):
        i = self.curIdx + idx
        return '' if i >= self.bufLen else self.buf[i]

    def _accept(self, start, end):
        val = self.buf[start:end]
        self.buf = self.buf[end:]
        self.bufLen = len(self.buf)
        if end > self.curIdx+1:
            self.col += (end - self.curIdx - 1)
        elif end < self.curIdx+1:
            self.col -= (self.curIdx - end + 1)
        self.curIdx = -1
        return val

    def _acceptLine(self, start):
        line = self.buf[start:]
        self.buf = ''
        self.bufLen = 0
        self.curIdx = -1
        return line

    def _getToken(self):
        state = STATE_START
        tokVal = ''
        tokType = TOK_EOF
        tokPos = (0,0)
        startIdx = 0
        hashSign = False

        while state != STATE_DONE:
            c = self._getNext()
            #print c, self.curIdx, self.row, self.col

            if state == STATE_START:
                if not c:
                    state = STATE_DONE
                elif c in ALPHA_CHARS:
                    tokPos = self.row, self.col
                    startIdx = self.curIdx
                    if self._lookahead(1) == '"':
                        tokType = TOK_STRING
                        state = STATE_STR
                        self._getNext()  # discard '"'
                    else:
                        tokType = TOK_IDENTIFIER
                        state = STATE_WORD
                elif c in DIGIT_CHARS:
                    tokType = TOK_NUMBER
                    tokPos = self.row, self.col
                    startIdx = self.curIdx
                    state = STATE_NUM
                elif c == '"':
                    tokType = TOK_STRING
                    tokPos = self.row, self.col
                    startIdx = self.curIdx
                    state = STATE_STR
                elif c == "'":
                    tokType = TOK_CHARACTER
                    tokPos = self.row, self.col
                    startIdx = self.curIdx
                    state = STATE_CHAR
                elif c in '~,;:{}()[]?':
                    tokType = TOK_OPERATOR
                    tokPos = self.row, self.col
                    tokVal = self._accept(self.curIdx, self.curIdx+1)
                    state = STATE_DONE
                elif c in IGNORE_CHARS:
                    startIdx = self.curIdx
                else:
                    if c in '=!' and self._lookahead(1) == '=':
                        tokPos = self.row, self.col
                        tokVal = self._accept(self.curIdx, self.curIdx+2)
                        tokType = TOK_OPERATOR
                        state = STATE_DONE
                    elif c in '*%^' and self._lookahead(1) == '=':
                        tokPos = self.row, self.col
                        tokVal = self._accept(self.curIdx, self.curIdx+2)
                        tokType = TOK_ASSIGN_OP
                        state = STATE_DONE
                    elif c == '/':
                        tokPos = self.row, self.col
                        nc = self._lookahead(1)
                        if nc == '*':
                            c = self._getNext() # avoid to accept '/' '*' '/'
                            tokType = TOK_COMMENT
                            startIdx = self.curIdx
                            state = STATE_BLOCK_COMMENT 
                        elif nc == '/':
                            tokVal = self._acceptLine(self.curIdx).rstrip(IGNORE_CHARS)
                            tokType = TOK_COMMENT
                            state = STATE_DONE
                        elif nc == '=':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_ASSIGN_OP
                            state = STATE_DONE
                        else:
                            tokVal = self._accept(self.curIdx, self.curIdx+1)
                            tokType = TOK_OPERATOR
                            state = STATE_DONE
                    elif c in '>':
                        tokPos = self.row, self.col
                        nc = self._lookahead(1)
                        if nc == '=':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_OPERATOR
                        elif nc == '>':
                            if self._lookahead(2) == '=':
                                tokVal = self._accept(self.curIdx, self.curIdx+3)
                                tokType = TOK_ASSIGN_OP
                            else:
                                tokVal = self._accept(self.curIdx, self.curIdx+2)
                                tokType = TOK_OPERATOR
                        else:
                            tokVal = self._accept(self.curIdx, self.curIdx+1)
                            tokType = TOK_OPERATOR
                        state = STATE_DONE
                    elif c in '<':
                        tokPos = self.row, self.col
                        nc = self._lookahead(1)
                        if nc == '=':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_OPERATOR
                        elif nc == '<':
                            if self._lookahead(2) == '=':
                                tokVal = self._accept(self.curIdx, self.curIdx+3)
                                tokType = TOK_ASSIGN_OP
                            else:
                                tokVal = self._accept(self.curIdx, self.curIdx+2)
                                tokType = TOK_OPERATOR
                        else:
                            tokVal = self._accept(self.curIdx, self.curIdx+1)
                            tokType = TOK_OPERATOR
                        state = STATE_DONE
                    elif c in '+':
                        tokPos = self.row, self.col
                        nc = self._lookahead(1)
                        if nc == '=':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_ASSIGN_OP
                        elif nc == '+':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_OPERATOR
                        else:
                            tokVal = self._accept(self.curIdx, self.curIdx+1)
                            tokType = TOK_OPERATOR
                        state = STATE_DONE
                    elif c in '-':
                        tokPos = self.row, self.col
                        nc = self._lookahead(1)
                        if nc == '=':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_ASSIGN_OP
                        elif nc == '-' or nc == '>':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_OPERATOR
                        else:
                            tokVal = self._accept(self.curIdx, self.curIdx+1)
                            tokType = TOK_OPERATOR
                        state = STATE_DONE
                    elif c in '&':
                        tokPos = self.row, self.col
                        nc = self._lookahead(1)
                        if nc == '=':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_ASSIGN_OP
                        elif nc == '&':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_OPERATOR
                        else:
                            tokVal = self._accept(self.curIdx, self.curIdx+1)
                            tokType = TOK_OPERATOR
                        state = STATE_DONE
                    elif c in '|':
                        tokPos = self.row, self.col
                        nc = self._lookahead(1)
                        if nc == '=':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_ASSIGN_OP
                        elif nc == '|':
                            tokVal = self._accept(self.curIdx, self.curIdx+2)
                            tokType = TOK_OPERATOR
                        else:
                            tokVal = self._accept(self.curIdx, self.curIdx+1)
                            tokType = TOK_OPERATOR
                        state = STATE_DONE
                    elif c == '.' and self._lookahead(1) == '.':
                        tokPos = self.row, self.col
                        tokVal = self._accept(self.curIdx, self.curIdx+3)
                        tokType = TOK_ELLIPSIS
                        state = STATE_DONE
                    elif c in '#' and self._lookahead(1) == '#':
                        tokPos = self.row, self.col
                        tokVal = self._accept(self.curIdx, self.curIdx+2)
                        tokType = TOK_CONCAT_OP
                        state = STATE_DONE
                    else:
                        tokPos = self.row, self.col
                        tokVal = self._accept(self.curIdx, self.curIdx+1)
                        if c == '=':
                            tokType = TOK_ASSIGN_OP
                        elif c == '#':
                            tokType = TOK_OPERATOR
                            hashSign = True
                        else:
                            tokType = TOK_OPERATOR
                        state = STATE_DONE

            elif state == STATE_WORD:
                if not c or not c in ALNUM_CHARS:
                    tokVal = self._accept(startIdx, self.curIdx)
                    state = STATE_DONE

            elif state == STATE_NUM:
                if not c or not c in NUM_CHARS:
                    tokVal = self._accept(startIdx, self.curIdx)
                    state = STATE_DONE

            elif state == STATE_BLOCK_COMMENT:
                if c == '*':
                    state = STATE_BLOCK_COMMENT_STAR

            elif state == STATE_BLOCK_COMMENT_STAR:
                if c == '/':
                    tokVal = self._accept(startIdx, self.curIdx+1)
                    state = STATE_DONE
                elif c != '*':
                    state = STATE_BLOCK_COMMENT

            elif state == STATE_STR:
                if c == '"':
                    tokVal = self._accept(startIdx, self.curIdx+1)
                    state = STATE_DONE
                elif c == '\\':
                    state = STATE_STR_ESCAPED

            elif state == STATE_STR_ESCAPED:
                state = STATE_STR

            elif state == STATE_CHAR:
                if c == "'":
                    tokVal = self._accept(startIdx, self.curIdx+1)
                    state = STATE_DONE
                elif c == '\\':
                    state = STATE_CHAR_ESCAPED

            elif state == STATE_CHAR_ESCAPED:
                state = STATE_CHAR

            else:
                raw_input('*** scan error ***')

        #
        # check if word is reserved keyword
        #
        if tokType == TOK_IDENTIFIER:
            if self.hashSign:
                tokType = ppReservedWords.get(tokVal, tokType)
            else:
                tokType = reservedWords.get(tokVal, tokType)

        self.hashSign = hashSign

        return tokType, tokVal, tokPos[0], tokPos[1]

