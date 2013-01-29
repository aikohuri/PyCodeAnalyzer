i = 0

TOK_EOF         = i; i += 1
TOK_COMMENT     = i; i += 1 # /*...*/ and //...

# preprocessor directives
TOK_PP_DEFINE      = i; i += 1
TOK_PP_UNDEF       = i; i += 1
TOK_PP_IF          = i; i += 1
TOK_PP_IFDEF       = i; i += 1
TOK_PP_IFNDEF      = i; i += 1
TOK_PP_ELIF        = i; i += 1
TOK_PP_ELSE        = i; i += 1
TOK_PP_ENDIF       = i; i += 1
TOK_PP_IMPORT      = i; i += 1
TOK_PP_INCLUDE     = i; i += 1
TOK_PP_INCLUDE_NEXT= i; i += 1
TOK_PP_IDENT       = i; i += 1
TOK_PP_LINE        = i; i += 1
TOK_PP_PRAGMA      = i; i += 1
TOK_PP_USING       = i; i += 1
TOK_PP_WARNING     = i; i += 1
TOK_PP_ERROR       = i; i += 1
TOK_PP_DEFINED     = i; i += 1

# C reserved keywords
TOK_STORAGE_CLASS = 0x00000100
i = 1
TOK_TYPEDEF     = TOK_STORAGE_CLASS + i; i += 1
TOK_EXTERN      = TOK_STORAGE_CLASS + i; i += 1
TOK_STATIC      = TOK_STORAGE_CLASS + i; i += 1
TOK_AUTO        = TOK_STORAGE_CLASS + i; i += 1
TOK_REGISTER    = TOK_STORAGE_CLASS + i; i += 1

TOK_FUNC_SPEC = 0x00000200
TOK_INLINE      = TOK_FUNC_SPEC

TOK_TYPE_QUAL = 0x00000400
i = 1
TOK_CONST       = TOK_TYPE_QUAL + i; i += 1
TOK_RESTRICT    = TOK_TYPE_QUAL + i; i += 1
TOK_VOLATILE    = TOK_TYPE_QUAL + i; i += 1

TOK_TYPE_SPEC = 0x00000800
i = 1
# do not change order
TOK_VOID        = TOK_TYPE_SPEC + i; i += 1
TOK_CHAR        = TOK_TYPE_SPEC + i; i += 1
TOK_SHORT       = TOK_TYPE_SPEC + i; i += 1
TOK_INT         = TOK_TYPE_SPEC + i; i += 1
TOK_LONG        = TOK_TYPE_SPEC + i; i += 1
TOK_FLOAT       = TOK_TYPE_SPEC + i; i += 1
TOK_DOUBLE      = TOK_TYPE_SPEC + i; i += 1
TOK_SIGNED      = TOK_TYPE_SPEC + i; i += 1
TOK_UNSIGNED    = TOK_TYPE_SPEC + i; i += 1
TOK_BOOL        = TOK_TYPE_SPEC + i; i += 1
TOK_COMPLEX     = TOK_TYPE_SPEC + i; i += 1
TOK_IMAGINARY   = TOK_TYPE_SPEC + i; i += 1
TOK_TYPEOF      = TOK_TYPE_SPEC + i; i += 1    
TOK_STRUCT      = TOK_TYPE_SPEC + i; i += 1
TOK_UNION       = TOK_TYPE_SPEC + i; i += 1
TOK_ENUM        = TOK_TYPE_SPEC + i; i += 1

# do not change order
TOK_CONSTANT = 0x00001000
i = 1
TOK_NUMBER      = TOK_CONSTANT + i; i += 1
TOK_CHARACTER   = TOK_CONSTANT + i; i += 1
TOK_STRING      = TOK_CONSTANT + i; i += 1

TOK_IDENTIFIER  = 0x00002000

TOK_STATEMENT = 0x00004000
i = 1
# do not change order
TOK_CASE        = TOK_STATEMENT + i; i += 1
TOK_DEFAULT     = TOK_STATEMENT + i; i += 1
TOK_SWITCH      = TOK_STATEMENT + i; i += 1
TOK_IF          = TOK_STATEMENT + i; i += 1
TOK_ELSE        = TOK_STATEMENT + i; i += 1
TOK_FOR         = TOK_STATEMENT + i; i += 1
TOK_DO          = TOK_STATEMENT + i; i += 1
TOK_WHILE       = TOK_STATEMENT + i; i += 1
TOK_GOTO        = TOK_STATEMENT + i; i += 1
TOK_CONTINUE    = TOK_STATEMENT + i; i += 1
TOK_BREAK       = TOK_STATEMENT + i; i += 1
TOK_RETURN      = TOK_STATEMENT + i; i += 1

TOK_SIZEOF = 0x00008000

TOK_OPERATOR = 0x00010000
i = 1
TOK_ELLIPSIS    = TOK_OPERATOR + i; i += 1 # "..."
TOK_CONCAT_OP   = TOK_OPERATOR + i; i += 1 # "##"
TOK_ASSIGN_OP   = TOK_OPERATOR + i; i += 1

ppReservedWords = {
    "define"      : TOK_PP_DEFINE,
    "if"          : TOK_PP_IF,
    "elif"        : TOK_PP_ELIF,
    "else"        : TOK_PP_ELSE,
    "endif"       : TOK_PP_ENDIF,
    "error"       : TOK_PP_ERROR,
    "ifdef"       : TOK_PP_IFDEF,
    "ifndef"      : TOK_PP_IFNDEF,
    "import"      : TOK_PP_IMPORT,
    "include"     : TOK_PP_INCLUDE,
    "include_next": TOK_PP_INCLUDE_NEXT,
    "ident"       : TOK_PP_IDENT,
    "line"        : TOK_PP_LINE,
    "pragma"      : TOK_PP_PRAGMA,
    "undef"       : TOK_PP_UNDEF,
    "using"       : TOK_PP_USING,
    "warning"     : TOK_PP_WARNING,
}

reservedWords = {
    "defined"   : TOK_PP_DEFINED,

    "auto"      : TOK_AUTO,
    "_Bool"     : TOK_BOOL,
    "break"     : TOK_BREAK,
    "case"      : TOK_CASE,
    "char"      : TOK_CHAR,
    "_Complex"  : TOK_COMPLEX,
    "const"     : TOK_CONST,
    "continue"  : TOK_CONTINUE,
    "default"   : TOK_DEFAULT,
    "do"        : TOK_DO,
    "double"    : TOK_DOUBLE,
    "else"      : TOK_ELSE,
    "enum"      : TOK_ENUM,
    "extern"    : TOK_EXTERN,
    "float"     : TOK_FLOAT,
    "for"       : TOK_FOR,
    "goto"      : TOK_GOTO,
    "if"        : TOK_IF,
    "_Imaginary": TOK_IMAGINARY,
    "typeof"    : TOK_TYPEOF,
    "inline"    : TOK_INLINE,
    "int"       : TOK_INT,
    "long"      : TOK_LONG,
    "register"  : TOK_REGISTER,
    "restrict"  : TOK_RESTRICT,
    "return"    : TOK_RETURN,
    "short"     : TOK_SHORT,
    "signed"    : TOK_SIGNED,
    "sizeof"    : TOK_SIZEOF,
    "static"    : TOK_STATIC,
    "struct"    : TOK_STRUCT,
    "switch"    : TOK_SWITCH,
    "typedef"   : TOK_TYPEDEF,
    "union"     : TOK_UNION,
    "unsigned"  : TOK_UNSIGNED,
    "void"      : TOK_VOID,
    "volatile"  : TOK_VOLATILE,
    "while"     : TOK_WHILE,
}

i = 0
STATE_START         = i; i += 1
STATE_BLOCK_COMMENT = i; i += 1
STATE_BLOCK_COMMENT_STAR = i; i += 1
STATE_NUM           = i; i += 1
STATE_WORD          = i; i += 1
STATE_CHAR          = i; i += 1
STATE_CHAR_ESCAPED  = i; i += 1
STATE_STR           = i; i += 1
STATE_STR_ESCAPED   = i; i += 1
STATE_DONE          = i; i += 1

ALPHA_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
DIGIT_CHARS = '0123456789'
ALNUM_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789'
NUM_CHARS   = '.0123456789abcdefABCDEFpPxXuUlL'
IGNORE_CHARS = ' \t\v\r\n\f'

i = 0
TOK_TYPE  = i; i += 1
TOK_VALUE = i; i += 1
TOK_ROW   = i; i += 1
TOK_COL   = i; i += 1
