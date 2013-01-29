NODE_TYPE  = 0
NODE_VALUE = 1

NODE = 0x10000000
i = 0
NODE_EXTERNAL_DECLARATION              = NODE + i; i += 1
NODE_DECLARATION                       = NODE + i; i += 1
NODE_FUNCTION_DEFINITION               = NODE + i; i += 1
NODE_DECLARATION_SPECIFIERS            = NODE + i; i += 1
NODE_PARAMETER_LIST                    = NODE + i; i += 1
NODE_PARAMETER_DECLARATION             = NODE + i; i += 1
NODE_ABSTRACT_DECLARATOR               = NODE + i; i += 1
NODE_DIRECT_ABSTRACT_DECLARATOR        = NODE + i; i += 1
NODE_DIRECT_ABSTRACT_DECLARATOR_SUFFIX = NODE + i; i += 1
NODE_POINTER                           = NODE + i; i += 1
NODE_TYPE_QUALIFIER_LIST               = NODE + i; i += 1
NODE_CONSTANT_EXPRESSION               = NODE + i; i += 1
NODE_BINARY_EXPRESSION                 = NODE + i; i += 1
NODE_CAST_EXPRESSION                   = NODE + i; i += 1
NODE_CAST                              = NODE + i; i += 1
NODE_UNARY_EXPRESSION                  = NODE + i; i += 1
NODE_TYPE_NAME                         = NODE + i; i += 1
NODE_POSTFIX_EXPRESSION                = NODE + i; i += 1
NODE_INITIALIZER_BLOCK                 = NODE + i; i += 1
NODE_POSTFIX_EXPRESSION_SUFFIX         = NODE + i; i += 1
NODE_EXPRESSION                        = NODE + i; i += 1
NODE_ASSIGNMENT_EXPRESSION             = NODE + i; i += 1
NODE_INIT_DECLARATOR_LIST              = NODE + i; i += 1
NODE_INIT_DECLARATOR                   = NODE + i; i += 1
NODE_INITIALIZER                       = NODE + i; i += 1
NODE_INITIALIZER_LIST                  = NODE + i; i += 1
NODE_LABELED_STATEMENT                 = NODE + i; i += 1
NODE_COMPOUND_STATEMENT                = NODE + i; i += 1
NODE_BLOCK_ITEM_LIST                   = NODE + i; i += 1
NODE_BLOCK_ITEM                        = NODE + i; i += 1
NODE_STATEMENT                         = NODE + i; i += 1
NODE_EXPRESSION_STATEMENT              = NODE + i; i += 1
NODE_SELECTION_STATEMENT               = NODE + i; i += 1
NODE_ITERATION_STATEMENT               = NODE + i; i += 1
NODE_JUMP_STATEMENT                    = NODE + i; i += 1
NODE_DECLARATION_LIST                  = NODE + i; i += 1
NODE_DECLARTION                        = NODE + i; i += 1
NODE_FUNCTION_SPECIFIER                = NODE + i; i += 1
NODE_STORAGE_CLASS_SPECIFIER           = NODE + i; i += 1
NODE_TYPE_SPECIFIER                    = NODE + i; i += 1
NODE_STRUCT_OR_UNION_SPECIFIER         = NODE + i; i += 1
NODE_STRUCT_DECLARATION_LIST           = NODE + i; i += 1
NODE_STRUCT_DECLARATION                = NODE + i; i += 1
NODE_SPECIFIER_QUALIFIER_LIST          = NODE + i; i += 1
NODE_STRUCT_DECLARATOR_LIST            = NODE + i; i += 1
NODE_STRUCT_DECLARATOR                 = NODE + i; i += 1
NODE_DECLARATOR                        = NODE + i; i += 1
NODE_DIRECT_DECLARATOR                 = NODE + i; i += 1
NODE_DIRECT_DECLARATOR_SUFFIX          = NODE + i; i += 1
NODE_PARAMETER_SPECIFIER               = NODE + i; i += 1
NODE_DIMENSION_SPECIFIER               = NODE + i; i += 1
NODE_IDENTIFIER_LIST                   = NODE + i; i += 1
NODE_ENUM_SPECIFIER                    = NODE + i; i += 1
NODE_ENUMERATOR_LIST                   = NODE + i; i += 1
NODE_ENUMERATOR                        = NODE + i; i += 1
NODE_TYPE_QUALIFIER                    = NODE + i; i += 1
NODE_DESIGNATION                       = NODE + i; i += 1
NODE_DESIGNATOR_LIST                   = NODE + i; i += 1
NODE_DESIGNATOR                        = NODE + i; i += 1

node_type_to_str = {
    NODE_EXTERNAL_DECLARATION              : 'EXTERNAL_DECLARATION',
    NODE_DECLARATION                       : 'DECLARATION',
    NODE_FUNCTION_DEFINITION               : 'FUNCTION_DEFINITION',
    NODE_DECLARATION_SPECIFIERS            : 'DECLARATION_SPECIFIERS',
    NODE_PARAMETER_LIST                    : 'PARAMETER_LIST',
    NODE_PARAMETER_DECLARATION             : 'PARAMETER_DECLARATION',
    NODE_ABSTRACT_DECLARATOR               : 'ABSTRACT_DECLARATOR',
    NODE_DIRECT_ABSTRACT_DECLARATOR        : 'DIRECT_ABSTRACT_DECLARATOR',
    NODE_DIRECT_ABSTRACT_DECLARATOR_SUFFIX : 'DIRECT_ABSTRACT_DECLARATOR_SUFFIX',
    NODE_POINTER                           : 'POINTER',
    NODE_TYPE_QUALIFIER_LIST               : 'TYPE_QUALIFIER_LIST',
    NODE_CONSTANT_EXPRESSION               : 'CONSTANT_EXPRESSION',
    NODE_BINARY_EXPRESSION                 : 'BINARY_EXPRESSION',
    NODE_CAST_EXPRESSION                   : 'CAST_EXPRESSION',
    NODE_CAST                              : 'CAST',
    NODE_UNARY_EXPRESSION                  : 'UNARY_EXPRESSION',
    NODE_TYPE_NAME                         : 'TYPE_NAME',
    NODE_POSTFIX_EXPRESSION                : 'POSTFIX_EXPRESSION',
    NODE_INITIALIZER_BLOCK                 : 'INITIALIZER_BLOCK',
    NODE_POSTFIX_EXPRESSION_SUFFIX         : 'POSTFIX_EXPRESSION_SUFFIX',
    NODE_EXPRESSION                        : 'EXPRESSION',
    NODE_ASSIGNMENT_EXPRESSION             : 'ASSIGNMENT_EXPRESSION',
    NODE_INIT_DECLARATOR_LIST              : 'INIT_DECLARATOR_LIST',
    NODE_INIT_DECLARATOR                   : 'INIT_DECLARATOR',
    NODE_INITIALIZER                       : 'INITIALIZER',
    NODE_INITIALIZER_LIST                  : 'INITIALIZER_LIST',
    NODE_LABELED_STATEMENT                 : 'LABELED_STATEMENT',
    NODE_COMPOUND_STATEMENT                : 'COMPOUND_STATEMENT',
    NODE_BLOCK_ITEM_LIST                   : 'BLOCK_ITEM_LIST',
    NODE_BLOCK_ITEM                        : 'BLOCK_ITEM',
    NODE_STATEMENT                         : 'STATEMENT',
    NODE_EXPRESSION_STATEMENT              : 'EXPRESSION_STATEMENT',
    NODE_SELECTION_STATEMENT               : 'SELECTION_STATEMENT',
    NODE_ITERATION_STATEMENT               : 'ITERATION_STATEMENT',
    NODE_JUMP_STATEMENT                    : 'JUMP_STATEMENT',
    NODE_DECLARATION_LIST                  : 'DECLARATION_LIST',
    NODE_DECLARTION                        : 'DECLARTION',
    NODE_FUNCTION_SPECIFIER                : 'FUNCTION_SPECIFIER',
    NODE_STORAGE_CLASS_SPECIFIER           : 'STORAGE_CLASS_SPECIFIER',
    NODE_TYPE_SPECIFIER                    : 'TYPE_SPECIFIER',
    NODE_STRUCT_OR_UNION_SPECIFIER         : 'STRUCT_OR_UNION_SPECIFIER',
    NODE_STRUCT_DECLARATION_LIST           : 'STRUCT_DECLARATION_LIST',
    NODE_STRUCT_DECLARATION                : 'STRUCT_DECLARATION',
    NODE_SPECIFIER_QUALIFIER_LIST          : 'SPECIFIER_QUALIFIER_LIST',
    NODE_STRUCT_DECLARATOR_LIST            : 'STRUCT_DECLARATOR_LIST',
    NODE_STRUCT_DECLARATOR                 : 'STRUCT_DECLARATOR',
    NODE_DECLARATOR                        : 'DECLARATOR',
    NODE_DIRECT_DECLARATOR                 : 'DIRECT_DECLARATOR',
    NODE_DIRECT_DECLARATOR_SUFFIX          : 'DIRECT_DECLARATOR_SUFFIX',
    NODE_PARAMETER_SPECIFIER               : 'PARAMETER_SPECIFIER',
    NODE_DIMENSION_SPECIFIER               : 'DIMENSION_SPECIFIER',
    NODE_IDENTIFIER_LIST                   : 'IDENTIFIER_LIST',
    NODE_ENUM_SPECIFIER                    : 'ENUM_SPECIFIER',
    NODE_ENUMERATOR_LIST                   : 'ENUMERATOR_LIST',
    NODE_ENUMERATOR                        : 'ENUMERATOR',
    NODE_TYPE_QUALIFIER                    : 'TYPE_QUALIFIER',
    NODE_DESIGNATION                       : 'DESIGNATION',
    NODE_DESIGNATOR_LIST                   : 'DESIGNATOR_LIST',
    NODE_DESIGNATOR                        : 'DESIGNATOR',
}

BUILTIN   = 0
VARIABLE  = 1
FUNCTION  = 2
TYPEDEF   = 3
DATA_TYPE = 4
ENUM_TYPE = 5

