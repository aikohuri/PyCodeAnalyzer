from collections import deque
from scanner import TOK_ROW


class TokenIterator:

    def __init__(self, iTokens):
        self.tokens = iTokens
        self.iter = iter(iTokens)
        self.tokenCache = deque()

    def setTokens(self, iTokens):
        self.tokens = iTokens
        self.iter = iter(iTokens)
        self.tokenCache = deque()

    def lookaheadToken(self, num):
        if num <= 0:
            raise IndexError('lookahead should be > 0')

        size = len(self.tokenCache)
        while num > size:
            self.tokenCache.append(self._getToken())
            size += 1
        return self.tokenCache[num-1]

    def getToken(self):
        if self.tokenCache:
            return self.tokenCache.popleft()
        else:
            return self._getToken()

    def getLineTokens(self):
        tokens = self.tokenCache
        token = self._getToken()

        if tokens:
            ln = tokens[-1][TOK_ROW]
        else:
            ln = token[TOK_ROW]

        while token and ln == token[TOK_ROW]:
            tokens.append(token)
            token = self._getToken()
        self.tokenCache = deque([token])
        return tokens

    def skipLine(self):
        token = self._getToken()

        if self.tokenCache:
            ln = self.tokenCache[-1][TOK_ROW]
            self.tokenCache.clear()
        else:
            ln = token[TOK_ROW]

        while token and ln == token[TOK_ROW]:
            token = self._getToken()

        self.tokenCache.append(token)

    def _getToken(self):
        try:
            return self.iter.next()
        except StopIteration:
            return None

