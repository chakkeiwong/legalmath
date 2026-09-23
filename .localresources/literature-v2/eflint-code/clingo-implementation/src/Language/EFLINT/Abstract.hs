module Language.EFLINT.Abstract where

import Language.EFLINT.Spec(Spec(..), TypeSpec(..), DomId(..), Derivation(..), Sync(..), Statement(..), TransType(..), Term(..), Domain(..), Var(..), Effect(..), EventSpec(..), Modifier(..), Kind(..), ActSpec(..), DutySpec(..), find_decl, chase_alias)

import Control.Exception(Exception, throw)
import Data.Char(chr, ord, isAsciiLower, isAsciiUpper, toLower, isNumber)
import Data.Data(Typeable)
import Data.List(foldl', intersperse, isPrefixOf)
import Debug.Trace(trace)
import qualified Data.Map as M
import qualified Data.Set as S


trace_show :: Show a => a-> a
trace_show arg = trace (show arg) arg


----- ERRORS -----
data AbstractException = NotYetImplemented
                       | NotABoolTerm Term
                       | NotOneInstTerm Term
                       | NotAnInstTerm Term
                       | UnexpectedProjTerm Term Var
                       | UndeclaredType String String
                       | UnsupportedAtomicStringType
                       | UnsupportedAtomicIntType
                       | UnsupportedAtomicStringClosedType
                       | UnsupportedAtomicIntClosedType
                       | UnsupportedTime
                       | UnsupportedCurrentTime
                       | EmptyProduct
                       | ExistsWithoutVars
                       | UndefinedEFlintType DomId
                       | ArityMismatch Int Int     -- got, expected
                       | UntagOnNonArityOneApp Term
                       | UnsupportedQuery Statement
                       | FieldNotGiven AbstractType AbstractField [AbstractField]
                       | PattThroughExprNotAPatt AbstractInstExpr
                       | InstThroughExprNotAnInst AbstractInstExpr
                       | Unreachable
                       | IllegalTupleTypify
                       | ReservedIdPrefix String DomId
                     deriving (Show, Typeable)
instance Exception AbstractException





----- REPRESENTATION -----
data AbstractArgs = AbstractArgsPrimitive AbstractInstExpr
                  | AbstractArgsComposite [(AbstractField, AbstractInstExpr)]
                  deriving (Eq, Ord, Show, Read)
data AbstractStruct = AbstractStruct String AbstractArgs
                    deriving (Eq, Ord, Show, Read)

data AbstractInst = AbstractInstStruct AbstractStruct
                  | AbstractInstInt Int
                  | AbstractInstString String
                  deriving (Eq, Ord, Show, Read)
data AbstractPatt = AbstractPattStruct AbstractStruct
                  | AbstractPattVar AbstractVar
                  | AbstractPattInt Int
                  | AbstractPattString String
                  deriving (Eq, Ord, Show, Read)

data AbstractBoolBinOp = AbstractBoolBinOpDisj
                       | AbstractBoolBinOpConj
                       deriving (Eq, Ord, Show, Read)
data AbstractInstBinOp = AbstractInstBinOpEq
                       | AbstractInstBinOpLt
                       deriving (Eq, Ord, Show, Read)
data AbstractAritBinOp = AbstractAritBinOpAdd
                       | AbstractAritBinOpSub
                       | AbstractAritBinOpMul
                       | AbstractAritBinOpDiv
                       | AbstractAritBinOpRem
                       deriving (Eq, Ord, Show, Read)
data AbstractBoolExpr = AbstractBoolExprTrue
                      | AbstractBoolExprNeg AbstractBoolExpr
                      | AbstractBoolExprCheck AbstractInputAttr AbstractInstExpr
                      | AbstractBoolExprBoolBinOp AbstractBoolBinOp AbstractBoolExpr AbstractBoolExpr
                      | AbstractBoolExprInstBinOp AbstractInstBinOp AbstractInstExpr AbstractInstExpr
                      deriving (Eq, Ord, Show, Read)

-- data AbstractPrimExpr = AbstractPrimExprString String
--                       | AbstractPrimExprInt Int
--                       | AbstractPrimExprProj AbstractAtomExpr AbstractField
--                       | AbstractPrimExprAggr AbstractAggr AbstractInstList
--                       | AbstractPrimExprBinOp AbstractAritBinOp AbstractPrimExpr AbstractPrimExpr
--                       | AbstractPrimExprVar String AbstractPrimitiveType
--                       deriving (Eq, Ord, Show, Read)
-- data AbstractAtomExpr = AbstractAtomExprPrim AbstractPrimExpr
--                       | AbstractAtomExprStruct AbstractStruct
--                       | AbstractAtomExprProj AbstractAtomExpr AbstractField
--                       | AbstractAtomExprVar String String
--                       deriving (Eq, Ord, Show, Read)
data AbstractInstExpr = AbstractInstExprStruct AbstractStruct
                      | AbstractInstExprProj AbstractInstExpr AbstractField
                      | AbstractInstExprAggr AbstractAggr AbstractInstList
                      | AbstractInstExprBinOp AbstractAritBinOp AbstractInstExpr AbstractInstExpr
                      | AbstractInstExprVar AbstractVar
                      | AbstractInstExprInt Int
                      | AbstractInstExprString String
                      deriving (Eq, Ord, Show, Read)
data AbstractInstList = AbstractInstListExpr AbstractInstExpr
                      | AbstractInstListFor AbstractInputAttr AbstractPatt AbstractInstList
                      | AbstractInstListWhere AbstractInstList AbstractBoolExpr
                      | AbstractInstListLet AbstractPatt AbstractInstExpr AbstractInstList
                      | AbstractInstListTuple [AbstractInstExpr]
                      deriving (Eq, Ord, Show, Read)

data AbstractAggr = AbstractAggrSum
                  | AbstractAggrCount
                  | AbstractAggrMin
                  | AbstractAggrMax
                  deriving (Eq, Ord, Show, Read)

data AbstractVar = AbstractVar {
                       vname :: String
                     , vty   :: AbstractType
                   }
                 deriving (Eq, Ord, Show, Read)

data AbstractType = AbstractTypeString
                  | AbstractTypeInt
                  | AbstractTypeFunc String
                  deriving (Eq, Ord, Show, Read)

data AbstractEffectAttr = AbstractEffectAttrTrigger
                        | AbstractEffectAttrCreate
                        | AbstractEffectAttrTerminate
                        | AbstractEffectAttrObfuscate
                        deriving (Eq, Ord, Show, Read)
data AbstractFilterAttr = AbstractFilterAttrSuppressed
                        | AbstractFilterAttrViolated
                        deriving (Eq, Ord, Show, Read)
data AbstractInputAttr = AbstractInputAttrEnum
                       | AbstractInputAttrHolds
                       | AbstractInputAttrEnabled
                       | AbstractInputAttrViolated
                       | AbstractInputAttrTrigger
                       | AbstractInputAttrActTrigger
                       deriving (Eq, Ord, Show, Read)
data AbstractOutputAttr = AbstractOutputAttrEnum
                        | AbstractOutputAttrAct
                        | AbstractOutputAttrDerived
                        | AbstractOutputAttrCreate
                        | AbstractOutputAttrTerminate
                        | AbstractOutputAttrObfuscate
                        | AbstractOutputAttrTrigger
                        | AbstractOutputAttrSuppressed
                        | AbstractOutputAttrViolated
                        deriving (Eq, Ord, Show, Read)
data AbstractClause = AbstractClauseDerive AbstractInstList
                    | AbstractClauseEffect AbstractInstList AbstractEffectAttr
                    | AbstractClauseFilter AbstractBoolExpr AbstractFilterAttr
                    | AbstractClauseFinite [AbstractInst]
                    | AbstractClauseInfinite
                    | AbstractClauseAct
                    deriving (Eq, Ord, Show, Read)

data AbstractPrimitiveType = AbstractPrimitiveTypeString | AbstractPrimitiveTypeInt
                           deriving (Eq, Ord, Show, Read)
data AbstractPrimitiveValue = AbstractPrimitiveValueString String | AbstractPrimitiveValueInt Int
                            deriving (Eq, Ord, Show, Read)
data AbstractPrimitiveValues = AbstractPrimitiveValuesString [String] | AbstractPrimitiveValuesInt [Int]
                             deriving (Eq, Ord, Show, Read)
-- Like an `AbstractVar` but different to be able to differentiate them during generation
data AbstractField = AbstractField {
                         fname :: String
                       , fty   :: AbstractType
                     }
                     deriving (Eq, Ord, Show, Read)
data AbstractFields = AbstractFieldsAtomicOpen AbstractPrimitiveType
                    | AbstractFieldsAtomicClose AbstractPrimitiveValues
                    | AbstractFieldsComposite [AbstractField]
                    deriving (Eq, Ord, Show, Read)

type AbstractTuple = (AbstractSpec, String, AbstractClause)

data AbstractTypeSpec = AbstractTypeSpec AbstractFields (S.Set AbstractClause)
                      deriving (Eq, Ord, Show, Read)
data AbstractSpec = AbstractSpec (M.Map String AbstractTypeSpec)
                  deriving (Eq, Ord, Show, Read)
data AbstractGroup = AbstractGroup [(AbstractInstList, AbstractEffectAttr)]
                   deriving (Eq, Ord, Show, Read)
data AbstractScenario = AbstractScenario [AbstractGroup]
                      deriving (Eq, Ord, Show, Read)


tupleAsInstLists :: AbstractTuple -> [AbstractInstList]
tupleAsInstLists (spec, ty, clause) = case clause of
    AbstractClauseDerive list -> [list]
    AbstractClauseEffect list effect -> [AbstractInstListWhere list (AbstractBoolExprCheck AbstractInputAttrTrigger (pattAsInstExpr (fieldPattFields ty spec clause)))]
    AbstractClauseFilter bexpr filter -> (\patt -> [AbstractInstListFor AbstractInputAttrEnum patt (AbstractInstListWhere (AbstractInstListExpr (pattAsInstExpr patt)) bexpr)]) (fieldPattFields ty spec clause)
    AbstractClauseInfinite -> [AbstractInstListFor AbstractInputAttrHolds (fieldPattFields ty spec clause) (AbstractInstListExpr (pattAsInstExpr (fieldPattFields ty spec clause)))]
    AbstractClauseFinite insts -> map (AbstractInstListExpr . AbstractInstExprStruct . (AbstractStruct ty) . AbstractArgsPrimitive . instAsInstExpr) insts
    AbstractClauseAct -> [AbstractInstListFor AbstractInputAttrTrigger (fieldPattFields ty spec clause) (AbstractInstListExpr (pattAsInstExpr (fieldPattFields ty spec clause)))]

typeSpecAsTuples :: AbstractSpec -> String -> AbstractTypeSpec -> [AbstractTuple]
typeSpecAsTuples spec ty (AbstractTypeSpec _ clauses) = map ((\spec ty clause -> (spec, ty, clause)) spec ty) (S.elems clauses)
specAsTuples :: AbstractSpec -> [AbstractTuple]
specAsTuples spec@(AbstractSpec tys) = foldl' (++) [] (M.mapWithKey (typeSpecAsTuples spec) tys)

effectAttrAsOutputAttr :: AbstractEffectAttr -> AbstractOutputAttr
effectAttrAsOutputAttr effect = case effect of
    AbstractEffectAttrCreate -> AbstractOutputAttrCreate
    AbstractEffectAttrTerminate -> AbstractOutputAttrTerminate
    AbstractEffectAttrObfuscate -> AbstractOutputAttrObfuscate
    AbstractEffectAttrTrigger -> AbstractOutputAttrTrigger
filterAttrAsOutputAttr :: AbstractFilterAttr -> AbstractOutputAttr
filterAttrAsOutputAttr filter = case filter of
    AbstractFilterAttrSuppressed -> AbstractOutputAttrSuppressed
    AbstractFilterAttrViolated -> AbstractOutputAttrViolated

instAsInstExpr :: AbstractInst -> AbstractInstExpr
instAsInstExpr inst = case inst of
    AbstractInstStruct struct -> AbstractInstExprStruct struct
    AbstractInstInt num -> AbstractInstExprInt num
    AbstractInstString string -> AbstractInstExprString string
pattAsInstExpr :: AbstractPatt -> AbstractInstExpr
pattAsInstExpr patt = case patt of
    AbstractPattStruct struct -> AbstractInstExprStruct struct
    AbstractPattVar var -> AbstractInstExprVar var
    AbstractPattInt num -> AbstractInstExprInt num
    AbstractPattString string -> AbstractInstExprString string

primitiveTypeAsType :: AbstractPrimitiveType -> AbstractType
primitiveTypeAsType ty = case ty of
    AbstractPrimitiveTypeString -> AbstractTypeString
    AbstractPrimitiveTypeInt -> AbstractTypeInt
primitiveValueAsType :: AbstractPrimitiveValue -> AbstractType
primitiveValueAsType value = case value of
    AbstractPrimitiveValueString _ -> AbstractTypeString
    AbstractPrimitiveValueInt _ -> AbstractTypeInt
primitiveValuesAsType :: AbstractPrimitiveValues -> AbstractType
primitiveValuesAsType values = case values of
    AbstractPrimitiveValuesString _ -> AbstractTypeString
    AbstractPrimitiveValuesInt _ -> AbstractTypeInt

instExprAsInst :: AbstractInstExpr -> AbstractInst
instExprAsInst iexpr = case iexpr of
    AbstractInstExprStruct struct -> AbstractInstStruct struct
    AbstractInstExprInt num -> AbstractInstInt num
    AbstractInstExprString string -> AbstractInstString string
    _ -> throw (InstThroughExprNotAnInst iexpr)
instExprAsPatt :: AbstractInstExpr -> AbstractPatt
instExprAsPatt iexpr = case iexpr of
    AbstractInstExprStruct struct -> AbstractPattStruct struct
    AbstractInstExprVar var -> AbstractPattVar var
    AbstractInstExprInt num -> AbstractPattInt num
    AbstractInstExprString string -> AbstractPattString string
    _ -> throw (PattThroughExprNotAPatt iexpr)

varAsField :: AbstractVar -> AbstractField
varAsField (AbstractVar name ty) = AbstractField name ty
fieldAsVar :: AbstractField -> AbstractVar
fieldAsVar (AbstractField name ty) = AbstractVar name ty





----- EFLINT UTILS -----
-- Removes dashes from an identifier
preprocessTyName :: String -> String
preprocessTyName "" = ""
preprocessTyName (c:rem) | isAsciiLower(c) || isNumber(c) || c == '\'' = [c] ++ (preprocessTyName rem)
preprocessTyName (c:rem) | isAsciiUpper(c) = [toLower(c)] ++ (preprocessTyName rem)
preprocessTyName (_:rem) = ['_'] ++ (preprocessTyName rem)

-- Both resolves _and_ chases an identifier.
resolveDomId :: Spec -> DomId -> Maybe TypeSpec
resolveDomId spec id = if not (isPrefixOf "aggr_" id)
                           then find_decl spec (chase_alias spec id)
                           else throw (ReservedIdPrefix "aggr_" id)





----- UNIQUE VAR GENERATION -----
-- Checks if a given ID is unique in a AbstractBoolExpr
idInAbstractBoolExpr :: String -> AbstractBoolExpr -> Bool
idInAbstractBoolExpr id bexpr = case bexpr of
    AbstractBoolExprTrue -> False
    AbstractBoolExprNeg bexpr -> idInAbstractBoolExpr id bexpr
    AbstractBoolExprCheck _ iexpr -> idInAbstractInstExpr id iexpr
    AbstractBoolExprBoolBinOp _ lhs rhs -> (idInAbstractBoolExpr id lhs) || (idInAbstractBoolExpr id rhs)
    AbstractBoolExprInstBinOp _ lhs rhs -> (idInAbstractInstExpr id lhs) || (idInAbstractInstExpr id rhs)
-- Checks if a given ID is unique in a AbstractInstExpr
idInAbstractInstExpr :: String -> AbstractInstExpr -> Bool
idInAbstractInstExpr id iexpr = case iexpr of
    AbstractInstExprInt _ -> False
    AbstractInstExprString _ -> False
    AbstractInstExprVar (AbstractVar name _) -> id == name
    AbstractInstExprProj iexpr (AbstractField name _) -> (idInAbstractInstExpr id iexpr) || (id == name)
    AbstractInstExprStruct (AbstractStruct _ args) -> case args of
        AbstractArgsPrimitive _ -> False
        AbstractArgsComposite args -> foldl' (||) False (map (\(_, iexpr) -> idInAbstractInstExpr id iexpr) args)
    AbstractInstExprAggr _ list -> idInAbstractInstList id list
    AbstractInstExprBinOp _ lhs rhs -> (idInAbstractInstExpr id lhs) || (idInAbstractInstExpr id rhs)
-- Checks if a given ID is unique in a AbstractInstList
idInAbstractInstList :: String -> AbstractInstList -> Bool
idInAbstractInstList id list = case list of
    AbstractInstListExpr iexpr -> idInAbstractInstExpr id iexpr
    AbstractInstListFor _ patt list -> (idInAbstractInstExpr id (pattAsInstExpr patt)) || (idInAbstractInstList id list)
    AbstractInstListWhere list bexpr -> (idInAbstractInstList id list) || (idInAbstractBoolExpr id bexpr)
    AbstractInstListLet patt iexpr list -> (idInAbstractInstExpr id (pattAsInstExpr patt)) || (idInAbstractInstExpr id iexpr) || (idInAbstractInstList id list)
    AbstractInstListTuple iexprs -> foldl' (||) False (map (idInAbstractInstExpr id) iexprs)
-- Checks if a given ID is unique in a AbstractClause
idInAbstractClause :: String -> AbstractClause -> Bool
idInAbstractClause id clause = case clause of 
    AbstractClauseDerive list -> (idInAbstractInstList id list)
    AbstractClauseEffect list _ -> (idInAbstractInstList id list)
    AbstractClauseFilter bexpr _ -> (idInAbstractBoolExpr id bexpr)
    AbstractClauseInfinite -> False
    AbstractClauseFinite insts -> foldl' (||) False (map ((idInAbstractInstExpr id) . instAsInstExpr) insts)
    AbstractClauseAct -> False

-- Given an identifier, "bumps" it one later.
bumpId :: String -> String
bumpId "" = "A"
bumpId id = if (ord (last id)) < (ord 'Z') then (init id) ++ [(chr ((ord (last id)) + 1))]
                                           else id ++ "A"
-- Given an identifier, "bumps" it one later. But then for lowercase identifiers.
bumpIdLowercase :: String -> String
bumpIdLowercase "" = "a"
bumpIdLowercase id = if (ord (last id)) < (ord 'z') then (init id) ++ [(chr ((ord (last id)) + 1))]
                                           else id ++ "z"

-- Returns an identifier that is guaranteed to be unique among variables in the given clause.
genUniqueId :: AbstractClause -> String
genUniqueId clause = genUniqueIdInner clause "a"
                     where genUniqueIdInner clause id = case (idInAbstractClause id clause) of
                                                            True -> genUniqueIdInner clause (bumpIdLowercase id)
                                                            False -> id

-- Returns an identifier that is guaranteed to be unique among variables in the given clause _and_ additional list of identifiers.
genUniqueIdInContext :: AbstractClause -> [String] -> String
genUniqueIdInContext clause context = genUniqueIdInner clause context "a"
                     where genUniqueIdInner clause context id = if (idInAbstractClause id clause) || (elem id context)
                                                                    then genUniqueIdInner clause context (bumpIdLowercase id)
                                                                    else id





----- FIELD PATTERNING -----
-- Given a type and a clause where it occurs, generates a field desugaring pattern for it
fieldPattFields :: String -> AbstractSpec -> AbstractClause -> AbstractPatt
fieldPattFields ty (AbstractSpec tys) clause = AbstractPattStruct (AbstractStruct ty (
    case (M.lookup ty tys) of
        Just (AbstractTypeSpec (AbstractFieldsAtomicOpen ty) _) -> AbstractArgsPrimitive (AbstractInstExprVar (AbstractVar (genUniqueId clause) (primitiveTypeAsType ty)))                   -- We still generate unique IDs, but now to avoid accidental conflict. These can't be quantified over anyway.
        Just (AbstractTypeSpec (AbstractFieldsAtomicClose values) _) -> AbstractArgsPrimitive (AbstractInstExprVar (AbstractVar (genUniqueId clause) (primitiveValuesAsType values)))        -- We still generate unique IDs, but now to avoid accidental conflict. These can't be quantified over anyway.
        Just (AbstractTypeSpec (AbstractFieldsComposite fields) _) -> AbstractArgsComposite (map (\field -> (field, AbstractInstExprVar (fieldAsVar field))) fields)
        Nothing -> throw (UndeclaredType "fieldPattFields" ty)
    ))

-- Given a type and a clause where it occurs, generates a field desugaring pattern for it that uses RANDOM new variables.
fieldPattUnique :: String -> AbstractSpec -> AbstractClause -> AbstractPatt
fieldPattUnique ty (AbstractSpec tys) clause = AbstractPattStruct (AbstractStruct ty (case (M.lookup ty tys) of
                                             Just (AbstractTypeSpec (AbstractFieldsAtomicOpen ty) _) -> AbstractArgsPrimitive (AbstractInstExprVar (AbstractVar (genUniqueId clause) (primitiveTypeAsType ty)))
                                             Just (AbstractTypeSpec (AbstractFieldsAtomicClose values) _) -> AbstractArgsPrimitive (AbstractInstExprVar (AbstractVar (genUniqueId clause) (primitiveValuesAsType values)))
                                             Just (AbstractTypeSpec (AbstractFieldsComposite fields) _) -> AbstractArgsComposite (foldl' (\context field@(AbstractField _ ty) -> (\id -> context ++ [(field, AbstractInstExprVar (AbstractVar id ty))]) (genUniqueIdInContext clause (map (\(_, iexpr) -> case iexpr of { AbstractInstExprVar (AbstractVar id _) -> id ; _ -> throw Unreachable}) context))) [] fields)
                                             Nothing -> throw (UndeclaredType "fieldPattUnique" ty)
                                         ))





----- PRINTING -----
ppAbstractInputAttr :: AbstractInputAttr -> String
ppAbstractInputAttr attr = case attr of
    AbstractInputAttrEnum -> "enum"
    AbstractInputAttrHolds -> "holds"
    AbstractInputAttrEnabled -> "enabled"
    AbstractInputAttrViolated -> "violated"
    AbstractInputAttrTrigger -> "trigger"
    AbstractInputAttrActTrigger -> "actTrigger"
ppAbstractOutputAttr :: AbstractOutputAttr -> String
ppAbstractOutputAttr attr = case attr of
    AbstractOutputAttrEnum -> "enum"
    AbstractOutputAttrAct -> "actTrigger"
    AbstractOutputAttrDerived -> "derived"
    AbstractOutputAttrCreate -> "create"
    AbstractOutputAttrTerminate -> "terminate"
    AbstractOutputAttrObfuscate -> "obfuscate"
    AbstractOutputAttrTrigger -> "trigger"
    AbstractOutputAttrSuppressed -> "suppressed"
    AbstractOutputAttrViolated -> "violated"

ppAbstractAggr :: AbstractAggr -> String
ppAbstractAggr aggr = case aggr of
    AbstractAggrCount -> "count"
    AbstractAggrSum -> "sum"
    AbstractAggrMax -> "max"
    AbstractAggrMin -> "min"
ppAbstractType :: AbstractType -> String
ppAbstractType ty = case ty of
    AbstractTypeString -> "String"
    AbstractTypeInt -> "Int"
    AbstractTypeFunc name -> name
ppAbstractBoolBinOp :: AbstractBoolBinOp -> String
ppAbstractBoolBinOp op = case op of
    AbstractBoolBinOpConj -> "&&"
    AbstractBoolBinOpDisj -> "||"
ppAbstractAritBinOp :: AbstractAritBinOp -> String
ppAbstractAritBinOp op = case op of
    AbstractAritBinOpAdd -> "+"
    AbstractAritBinOpSub -> "-"
    AbstractAritBinOpMul -> "*"
    AbstractAritBinOpDiv -> "/"
    AbstractAritBinOpRem -> "%"
ppAbstractInstBinOp :: AbstractInstBinOp -> String
ppAbstractInstBinOp op = case op of
    AbstractInstBinOpEq -> "=="
    AbstractInstBinOpLt -> "<"

ppAbstractArgs :: AbstractArgs -> String
ppAbstractArgs args = case args of
    AbstractArgsPrimitive iexpr -> ppAbstractInstExpr iexpr
    AbstractArgsComposite args -> (foldl' (++) "" (intersperse ", " (map (\(_, iexpr) -> ppAbstractInstExpr iexpr) args)))

ppAbstractVar :: AbstractVar -> String
ppAbstractVar (AbstractVar name ty) = "<" ++ (ppAbstractType ty) ++ ", \"" ++ name ++ "\">"
ppAbstractField :: AbstractField -> String
ppAbstractField (AbstractField name ty) = "<" ++ (ppAbstractType ty) ++ ", \"" ++ name ++ "\">"
ppAbstractFields :: AbstractFields -> String
ppAbstractFields fields = case fields of
    AbstractFieldsAtomicOpen AbstractPrimitiveTypeString -> "$S$"
    AbstractFieldsAtomicOpen AbstractPrimitiveTypeInt -> "$Z$"
    AbstractFieldsAtomicClose (AbstractPrimitiveValuesString dom) -> "$S$ -> (" ++ (foldl' (++) "" (intersperse ", " dom)) ++ ")"
    AbstractFieldsAtomicClose (AbstractPrimitiveValuesInt dom) -> "$Z$ -> (" ++ (foldl' (++) "" (intersperse ", " (map show dom))) ++ ")"
    AbstractFieldsComposite fields -> foldl' (++) "" (intersperse ", " (map ppAbstractField fields))



ppAbstractBoolExpr :: AbstractBoolExpr -> String
ppAbstractBoolExpr bexpr = case bexpr of
    AbstractBoolExprTrue -> "true"
    AbstractBoolExprNeg bexpr -> "not " ++ (ppAbstractBoolExpr bexpr)
    AbstractBoolExprCheck attr iexpr -> (ppAbstractInputAttr attr) ++ "(" ++ (ppAbstractInstExpr iexpr) ++ ")"
    AbstractBoolExprBoolBinOp op lhs rhs -> "(" ++ (ppAbstractBoolExpr lhs) ++ " " ++ (ppAbstractBoolBinOp op) ++ " " ++ (ppAbstractBoolExpr rhs) ++ ")"
    AbstractBoolExprInstBinOp op lhs rhs -> "(" ++ (ppAbstractInstExpr lhs) ++ " " ++ (ppAbstractInstBinOp op) ++ " " ++ (ppAbstractInstExpr rhs) ++ ")"

ppAbstractInstExpr :: AbstractInstExpr -> String
ppAbstractInstExpr iexpr = case iexpr of
    AbstractInstExprString lit -> "\"" ++ lit ++ "\""
    AbstractInstExprInt lit -> show lit
    AbstractInstExprVar var -> ppAbstractVar var
    AbstractInstExprProj iexpr field -> (ppAbstractInstExpr iexpr) ++ "." ++ (ppAbstractField field)
    AbstractInstExprStruct (AbstractStruct ty args) -> "struct(" ++ ty ++ ", " ++ (ppAbstractArgs args) ++ ")"
    AbstractInstExprBinOp op lhs rhs -> (ppAbstractInstExpr lhs) ++ " " ++ (ppAbstractAritBinOp op) ++ " " ++ (ppAbstractInstExpr rhs)
    AbstractInstExprAggr aggr list -> "aggr(" ++ (ppAbstractAggr aggr) ++ ", " ++ (ppAbstractInstList list) ++ ")"

ppAbstractInstList :: AbstractInstList -> String
ppAbstractInstList list = case list of
    AbstractInstListFor attr var list -> "for(" ++ (ppAbstractInputAttr attr) ++ ", " ++ (ppAbstractInstExpr (pattAsInstExpr var)) ++ ", " ++ (ppAbstractInstList list) ++ ")"
    AbstractInstListLet var iexpr list -> "let(" ++ (ppAbstractInstExpr (pattAsInstExpr var)) ++ ", " ++ (ppAbstractInstExpr iexpr) ++ ", " ++ (ppAbstractInstList list) ++ ")"
    AbstractInstListWhere list bexpr -> "where(" ++ (ppAbstractInstList list) ++ ", " ++ (ppAbstractBoolExpr bexpr) ++ ")"
    AbstractInstListExpr iexpr -> ppAbstractInstExpr iexpr
    AbstractInstListTuple iexprs -> foldl' (++) "" (intersperse ", " (map ppAbstractInstExpr iexprs))

ppAbstractClause :: AbstractClause -> String
ppAbstractClause clause = case clause of
    AbstractClauseDerive list -> "derive(" ++ (ppAbstractInstList list) ++ ")"
    AbstractClauseEffect list effect -> "effect(" ++ (ppAbstractInstList list) ++ ", " ++ (ppAbstractOutputAttr (effectAttrAsOutputAttr effect)) ++ ")"
    AbstractClauseFilter bexpr filter -> "filter(" ++ (ppAbstractBoolExpr bexpr) ++ ", " ++ (ppAbstractOutputAttr (filterAttrAsOutputAttr filter)) ++ ")"
    AbstractClauseInfinite -> "infinite"
    AbstractClauseFinite insts -> "finite(" ++ (foldl' (++) "" (intersperse ", " (map (ppAbstractInstExpr . instAsInstExpr) insts))) ++ ")"
    AbstractClauseAct -> "act"



ppAbstractTuple :: AbstractTuple -> String
ppAbstractTuple tuple@(spec, ty, clause) = case clause of
    AbstractClauseDerive _ -> "(s, " ++ ty ++ ", [" ++ (ppAbstractInstList (head (tupleAsInstLists tuple))) ++ ", derived])"
    AbstractClauseEffect _ effect -> "(s, " ++ ty ++ ", [" ++ (ppAbstractInstList (head (tupleAsInstLists tuple))) ++ ", " ++ (ppAbstractOutputAttr (effectAttrAsOutputAttr effect)) ++ "])"
    AbstractClauseFilter _ filter -> "(s, " ++ ty ++ ", [" ++ (ppAbstractInstList (head (tupleAsInstLists tuple))) ++ ", " ++ (ppAbstractOutputAttr (filterAttrAsOutputAttr filter)) ++ "])"
    AbstractClauseInfinite -> "(s, " ++ ty ++ ", [" ++ (ppAbstractInstList (head (tupleAsInstLists tuple))) ++ "], infinite)"
    AbstractClauseFinite insts -> "(s, " ++ ty ++ ", " ++ (foldl' (++) "" (map ppAbstractTupleInst insts)) ++ ", finite)"
                                  where ppAbstractTupleInst inst = "[" ++ ((ppAbstractInstExpr . instAsInstExpr) inst) ++ ", enum]"
    AbstractClauseAct -> "(s, " ++ ty ++ ", [" ++ (ppAbstractInstList (head (tupleAsInstLists tuple))) ++ "], act)"

ppAbstractTypeSpec :: AbstractSpec -> String -> AbstractTypeSpec -> String
ppAbstractTypeSpec spec ty (AbstractTypeSpec fields clauses) = ty ++ " |-> " ++ "<["
                                                               ++ (ppAbstractFields fields)
                                                               ++ "], ["
                                                               ++ (foldl' (++) "" (intersperse ", " (S.elems (S.map ((\spec ty clause -> "\n    " ++ ppAbstractTuple (spec, ty, clause)) spec ty) clauses))))
                                                               ++ (if (length clauses) > 0 then "\n" else "") ++ "]>\n"

ppAbstractSpec :: AbstractSpec -> String
ppAbstractSpec spec@(AbstractSpec tys) = M.foldlWithKey' ((\spec snippet ty def -> snippet ++ (ppAbstractTypeSpec spec ty def)) spec) "" tys

ppAbstractGroup :: AbstractSpec -> AbstractGroup -> String
ppAbstractGroup spec (AbstractGroup effects) = "{ " ++ (foldl' (++) "" (map (((flip (++)) ".") . ppAbstractClause . (uncurry AbstractClauseEffect)) effects)) ++ " }"

ppAbstractScenario :: AbstractSpec -> AbstractScenario -> String
ppAbstractScenario spec (AbstractScenario groups) = foldl' (++) "" (map (((flip (++)) "\n") . (ppAbstractGroup spec)) groups)





----- TYPE ANALYSIS -----
-- Computes the type of an instance expression.
typifyAbstractInstExpr :: AbstractInstExpr -> AbstractType
typifyAbstractInstExpr iexpr = case iexpr of
    AbstractInstExprString _ -> AbstractTypeString
    AbstractInstExprInt _ -> AbstractTypeInt
    AbstractInstExprVar (AbstractVar _ ty) -> ty
    AbstractInstExprStruct (AbstractStruct ty _) -> AbstractTypeFunc ty
    AbstractInstExprProj _ (AbstractField _ ty) -> ty
    AbstractInstExprBinOp _ _ _ -> AbstractTypeInt
    AbstractInstExprAggr _ _ -> AbstractTypeInt

-- Computes the type of an instance list.
typifyAbstractInstList :: AbstractInstList -> AbstractType
typifyAbstractInstList list = case list of
    AbstractInstListFor _ _ list -> typifyAbstractInstList list
    AbstractInstListLet _ _ list -> typifyAbstractInstList list
    AbstractInstListWhere list _ -> typifyAbstractInstList list
    AbstractInstListExpr iexpr -> typifyAbstractInstExpr iexpr
    AbstractInstListTuple _ -> throw IllegalTupleTypify





----- STAGE 0: TRANSLATION INTO ABSTRACT AST -----
abstractifyVar :: Spec -> Var -> AbstractVar
abstractifyVar spec (Var ty suffix) = case ty of
    "String" -> AbstractVar (ty ++ suffix) AbstractTypeString
    "Int" -> AbstractVar (ty ++ suffix) AbstractTypeInt
    _ -> AbstractVar (ty ++ suffix) (AbstractTypeFunc (preprocessTyName (chase_alias spec ty)))
abstractifyVarAsField :: Spec -> Var -> AbstractField
abstractifyVarAsField spec (Var ty suffix) = case ty of
    "String" -> AbstractField (ty ++ suffix) AbstractTypeString
    "Int" -> AbstractField (ty ++ suffix) AbstractTypeInt
    _ -> AbstractField (ty ++ suffix) (AbstractTypeFunc (preprocessTyName (chase_alias spec ty)))
abstractifyVarAsFieldKV :: Spec -> Var -> (AbstractField, AbstractInstExpr)
abstractifyVarAsFieldKV spec var = (abstractifyVarAsField spec var, AbstractInstExprVar (abstractifyVar spec var))
-- Recursive function to abstractify a list of vars to a sequence of foreach'es, one per var
abstractifyVarsAsFors :: Spec -> AbstractInputAttr -> [Var] -> AbstractInstList -> AbstractInstList
abstractifyVarsAsFors spec attr [] list = list
abstractifyVarsAsFors spec attr (var:vars) list = AbstractInstListFor attr (AbstractPattVar (abstractifyVar spec var)) (abstractifyVarsAsFors spec attr vars list)

abstractifyModifierAsKV :: Spec -> Modifier -> (AbstractField, AbstractInstExpr)
abstractifyModifierAsKV spec (Rename var iexpr) = (abstractifyVarAsField spec var, abstractifyInstOneTerm spec iexpr)

abstractifyBoolTerm :: Spec -> Term -> AbstractBoolExpr
abstractifyBoolTerm spec term = case term of
    Not bexpr -> AbstractBoolExprNeg (abstractifyBoolTerm spec bexpr)
    And lhs rhs -> AbstractBoolExprBoolBinOp AbstractBoolBinOpConj (abstractifyBoolTerm spec lhs) (abstractifyBoolTerm spec rhs)
    Or lhs rhs -> AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj (abstractifyBoolTerm spec lhs) (abstractifyBoolTerm spec rhs)
    BoolLit True -> AbstractBoolExprTrue
    BoolLit False -> AbstractBoolExprNeg (abstractifyBoolTerm spec (BoolLit True))

    Leq lhs rhs -> abstractifyBoolTerm spec (Geq rhs lhs)
    Geq lhs rhs -> AbstractBoolExprNeg (abstractifyBoolTerm spec (Le lhs rhs))
    Ge lhs rhs -> abstractifyBoolTerm spec (Le rhs lhs)
    Le lhs rhs -> AbstractBoolExprInstBinOp AbstractInstBinOpLt (abstractifyInstOneTerm spec lhs) (abstractifyInstOneTerm spec rhs)

    Eq lhs rhs -> AbstractBoolExprInstBinOp AbstractInstBinOpEq (abstractifyInstOneTerm spec lhs) (abstractifyInstOneTerm spec rhs)
    Neq lhs rhs -> AbstractBoolExprNeg (abstractifyBoolTerm spec (Eq lhs rhs))

    -- NOTE: Now we're formalizing as per the paper, `0 < #count { ... }`
    --       However, it is unclear how stable this is. This should also be possible:
    --       `foo(Y) :- 0<#count { y(X) : y(X), cool(X,Y) } , whatever(Y).`
    --       can simply be
    --       `foo(Y) :- y(X) ; cool(X,Y) ; whatever(Y).`
    Exists [] _ -> throw ExistsWithoutVars
    Exists (var:[]) bexpr -> AbstractBoolExprInstBinOp AbstractInstBinOpLt
                                 (AbstractInstExprInt 0)
                                 (abstractifyInstOneTerm spec (Count [var] (When (IntLit 1) bexpr)))      -- Note: we're looking for at least 1. So no need to worry about uniqueness.
    Exists (var:vars) bexpr -> AbstractBoolExprInstBinOp AbstractInstBinOpLt
                                   (AbstractInstExprInt 0)
                                   (abstractifyInstOneTerm spec (Count [var] (When (IntLit 1) (Exists vars bexpr))))
    Forall vars bexpr -> AbstractBoolExprNeg (abstractifyBoolTerm spec (Exists vars (Not bexpr)))
    Present iexpr -> AbstractBoolExprCheck AbstractInputAttrHolds (abstractifyInstOneTerm spec iexpr)
    Violated iexpr -> AbstractBoolExprCheck AbstractInputAttrViolated (abstractifyInstOneTerm spec iexpr)
    Enabled iexpr -> AbstractBoolExprCheck AbstractInputAttrEnabled (abstractifyInstOneTerm spec iexpr)
    Project iexpr field -> throw (UnexpectedProjTerm iexpr field)

    -- Other terms which aren't boolean expressions
    Sub _ _ -> throw (NotABoolTerm term)
    Add _ _ -> throw (NotABoolTerm term)
    Mult _ _ -> throw (NotABoolTerm term)
    Mod _ _ -> throw (NotABoolTerm term)
    Div _ _ -> throw (NotABoolTerm term)
    IntLit _ -> throw (NotABoolTerm term)
    StringLit _ -> throw (NotABoolTerm term)
    Count _ _ -> throw (NotABoolTerm term)
    Sum _ _ -> throw (NotABoolTerm term)
    Max _ _ -> throw (NotABoolTerm term)
    Min _ _ -> throw (NotABoolTerm term)
    When _ _ -> throw (NotABoolTerm term)
    Ref _ -> throw (NotABoolTerm term)
    App _ _ -> throw (NotABoolTerm term)
    Tag _ _ -> throw (NotABoolTerm term)
    Untag _ -> throw (NotABoolTerm term)
    CurrentTime -> throw (NotABoolTerm term)

-- Converts a Term to an instance expression which generates EXACTLY one instance.
abstractifyInstOneTerm :: Spec -> Term -> AbstractInstExpr
abstractifyInstOneTerm spec term = case term of
    Sub lhs rhs -> AbstractInstExprBinOp AbstractAritBinOpSub (abstractifyInstOneTerm spec lhs) (abstractifyInstOneTerm spec rhs)
    Add lhs rhs -> AbstractInstExprBinOp AbstractAritBinOpAdd (abstractifyInstOneTerm spec lhs) (abstractifyInstOneTerm spec rhs)
    Mult lhs rhs -> AbstractInstExprBinOp AbstractAritBinOpMul (abstractifyInstOneTerm spec lhs) (abstractifyInstOneTerm spec rhs)
    Mod lhs rhs -> AbstractInstExprBinOp AbstractAritBinOpRem (abstractifyInstOneTerm spec lhs) (abstractifyInstOneTerm spec rhs)
    Div lhs rhs -> AbstractInstExprBinOp AbstractAritBinOpDiv (abstractifyInstOneTerm spec lhs) (abstractifyInstOneTerm spec rhs)
    IntLit num -> AbstractInstExprInt num
    StringLit string -> AbstractInstExprString string

    Count vars iexpr -> AbstractInstExprAggr AbstractAggrCount (abstractifyVarsAsFors spec AbstractInputAttrEnum vars (abstractifyInstListTerm spec iexpr))
    Sum vars iexpr -> AbstractInstExprAggr AbstractAggrSum (abstractifyVarsAsFors spec AbstractInputAttrEnum vars (abstractifyInstListTerm spec iexpr))
    Max vars iexpr -> AbstractInstExprAggr AbstractAggrMax (abstractifyVarsAsFors spec AbstractInputAttrEnum vars (abstractifyInstListTerm spec iexpr))
    Min vars iexpr -> AbstractInstExprAggr AbstractAggrMin (abstractifyVarsAsFors spec AbstractInputAttrEnum vars (abstractifyInstListTerm spec iexpr))

    Ref var -> AbstractInstExprVar (abstractifyVar spec var)
    App ty (Left args) -> AbstractInstExprStruct (AbstractStruct (preprocessTyName (chase_alias spec ty)) (case (resolveDomId spec ty) of
                              Just decl -> case (domain decl) of
                                               -- TODO
                                               AnyString -> case args of
                                                                [arg] -> AbstractArgsPrimitive (abstractifyInstOneTerm spec arg)
                                                                _ -> throw (ArityMismatch (length args) 1)
                                               AnyInt -> case args of
                                                              [arg] -> AbstractArgsPrimitive (abstractifyInstOneTerm spec arg)
                                                              _ -> throw (ArityMismatch (length args) 1)
                                               Strings _ -> case args of
                                                                [arg] -> AbstractArgsPrimitive (abstractifyInstOneTerm spec arg)
                                                                _ -> throw (ArityMismatch (length args) 1)
                                               Ints _ -> case args of
                                                              [arg] -> AbstractArgsPrimitive (abstractifyInstOneTerm spec arg)
                                                              _ -> throw (ArityMismatch (length args) 1)
                                               -- Compiles to `Foreach <field1>: (Foreach <field2>: (<id>(<fields...>) Where <term>))
                                               Products vars -> case ((length args) == (length vars)) of
                                                                    True -> AbstractArgsComposite (zip (map (abstractifyVarAsField spec) vars) (map (abstractifyInstOneTerm spec) args))
                                                                    False -> throw (ArityMismatch (length args) (length vars))
                                               -- TODO(?)
                                               Time -> throw UnsupportedTime
                              Nothing   -> throw (UndefinedEFlintType ty)
                          ))
    App ty (Right args) -> case (resolveDomId spec ty) of
        Just tyspec -> case (domain tyspec) of
            AnyString -> case args of
                [Rename _ iexpr] -> AbstractInstExprStruct (AbstractStruct (preprocessTyName (chase_alias spec ty)) (AbstractArgsPrimitive (abstractifyInstOneTerm spec iexpr)))
                _ -> throw (ArityMismatch (length args) 1)
            AnyInt -> case args of
                [Rename _ iexpr] -> AbstractInstExprStruct (AbstractStruct (preprocessTyName (chase_alias spec ty)) (AbstractArgsPrimitive (abstractifyInstOneTerm spec iexpr)))
                _ -> throw (ArityMismatch (length args) 1)
            Strings _ -> case args of
                [Rename _ iexpr] -> AbstractInstExprStruct (AbstractStruct (preprocessTyName (chase_alias spec ty)) (AbstractArgsPrimitive (abstractifyInstOneTerm spec iexpr)))
                _ -> throw (ArityMismatch (length args) 1)
            Ints _ -> case args of
                [Rename _ iexpr] -> AbstractInstExprStruct (AbstractStruct (preprocessTyName (chase_alias spec ty)) (AbstractArgsPrimitive (abstractifyInstOneTerm spec iexpr)))
                _ -> throw (ArityMismatch (length args) 1)
            Products vars -> AbstractInstExprStruct (AbstractStruct (preprocessTyName (chase_alias spec ty)) (AbstractArgsComposite (map (\field -> case (M.lookup field values) of
                                                                                                              Just value -> (field, value)
                                                                                                              -- eFLINT only implicitly adds the missing fields, as it _does_ quantify over them
                                                                                                              -- Hence, we will do the adding ourselves. But we can do it naively, as any missing bindings
                                                                                                              -- (i.e., quantification) _is_ taken care of by the static eval.
                                                                                                              Nothing -> (field, AbstractInstExprVar (fieldAsVar field))
                                                                                               ) (map (abstractifyVarAsField spec) vars))))
                             where values = M.fromList (map ((\spec (Rename var iexpr) -> (abstractifyVarAsField spec var, abstractifyInstOneTerm spec iexpr)) spec) args)
            -- TODO(?)
            Time -> throw UnsupportedTime
        Nothing -> throw (UndeclaredType "abstractifyInstOneTerm" ty)
    Project iexpr var -> AbstractInstExprProj (abstractifyInstOneTerm spec iexpr) (abstractifyVarAsField spec var)
    CurrentTime -> throw UnsupportedCurrentTime

    -- Treat the internal two
    Tag term ty -> (abstractifyInstOneTerm spec (App ty (Left [term])))
    Untag term -> case term of
                      App ty (Left [arg]) -> (abstractifyInstOneTerm spec arg)
                      App _ _ -> throw (UntagOnNonArityOneApp term)
                      -- Let's just ignore any others
                      _ -> abstractifyInstOneTerm spec term

    -- Other terms which aren't instance expressions
    Not _ -> throw (NotOneInstTerm term)
    And _ _ -> throw (NotOneInstTerm term)
    Or _ _ -> throw (NotOneInstTerm term)
    BoolLit _ -> throw (NotOneInstTerm term)
    Leq _ _ -> throw (NotOneInstTerm term)
    Geq _ _ -> throw (NotOneInstTerm term)
    Ge _ _ -> throw (NotOneInstTerm term)
    Le _ _ -> throw (NotOneInstTerm term)
    Eq _ _ -> throw (NotOneInstTerm term)
    Neq _ _ -> throw (NotOneInstTerm term)
    Exists _ _ -> throw (NotOneInstTerm term)
    Forall _ _ -> throw (NotOneInstTerm term)
    Present _ -> throw (NotOneInstTerm term)
    Violated _ -> throw (NotOneInstTerm term)
    Enabled _ -> throw (NotOneInstTerm term)

    -- Special case which isn't a single expression, it's a list of 0 or 1 items!
    When list bexpr -> case (list, bexpr) of
        -- There's ONE saving grace for the When
        -- We shall naively try to convert the `list` instead
        (list, (BoolLit True)) -> abstractifyInstOneTerm spec list
        _ -> throw (NotOneInstTerm term)

-- Generalization of `abstractifyInstOneTerm` which also allows zero instances (i.e., a Where)
abstractifyInstListTerm :: Spec -> Term -> AbstractInstList
abstractifyInstListTerm spec term = case term of
    -- The special one
    When iexpr bexpr -> AbstractInstListWhere (abstractifyInstListTerm spec iexpr) (abstractifyBoolTerm spec bexpr)

    -- All of these are the same as the exactly-one-expression case
    Sub _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Add _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Mult _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Mod _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Div _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    IntLit _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    StringLit _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Count _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Sum _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Max _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Min _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Ref _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    App _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Project _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    CurrentTime -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Tag _ _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)
    Untag _ -> AbstractInstListExpr (abstractifyInstOneTerm spec term)

    -- Other terms which aren't instance expressions
    Not _ -> throw (NotAnInstTerm term)
    And _ _ -> throw (NotAnInstTerm term)
    Or _ _ -> throw (NotAnInstTerm term)
    BoolLit _ -> throw (NotAnInstTerm term)
    Leq _ _ -> throw (NotAnInstTerm term)
    Geq _ _ -> throw (NotAnInstTerm term)
    Ge _ _ -> throw (NotAnInstTerm term)
    Le _ _ -> throw (NotAnInstTerm term)
    Eq _ _ -> throw (NotAnInstTerm term)
    Neq _ _ -> throw (NotAnInstTerm term)
    Exists _ _ -> throw (NotAnInstTerm term)
    Forall _ _ -> throw (NotAnInstTerm term)
    Present _ -> throw (NotAnInstTerm term)
    Violated _ -> throw (NotAnInstTerm term)
    Enabled _ -> throw (NotAnInstTerm term)

abstractifyDerivation :: Spec -> DomId -> Domain -> Derivation -> AbstractClause
abstractifyDerivation spec id dom der = case der of
    (Dv [] term) -> AbstractClauseDerive (abstractifyInstListTerm spec term)
    (Dv (var:vars) term) -> AbstractClauseDerive (AbstractInstListWhere (abstractifyInstListTerm spec term) (foldl' (AbstractBoolExprBoolBinOp AbstractBoolBinOpConj) (((AbstractBoolExprCheck AbstractInputAttrEnum) . AbstractInstExprVar . (abstractifyVar spec)) var) (map ((AbstractBoolExprCheck AbstractInputAttrEnum) . AbstractInstExprVar . (abstractifyVar spec)) vars)))
    (HoldsWhen term) -> AbstractClauseDerive (case dom of
                            -- TODO
                            AnyString -> throw UnsupportedAtomicStringType
                            AnyInt -> throw UnsupportedAtomicIntType
                            Strings _ -> throw UnsupportedAtomicStringClosedType
                            Ints _ -> throw UnsupportedAtomicIntClosedType
                            -- Compiles to `Foreach <field1>: (Foreach <field2>: (<id>(<fields...>) Where <term>))
                            Products vars -> abstractifyVarsAsFors spec AbstractInputAttrEnum vars (AbstractInstListWhere (AbstractInstListExpr (AbstractInstExprStruct (AbstractStruct (preprocessTyName (chase_alias spec id)) (AbstractArgsComposite (map (abstractifyVarAsFieldKV spec) vars))))) (abstractifyBoolTerm spec term))
                            -- TODO(?)
                            Time -> throw UnsupportedTime
                        )

abstractifyCondition :: Spec -> Term -> AbstractClause
abstractifyCondition spec bexpr = AbstractClauseFilter (AbstractBoolExprNeg (abstractifyBoolTerm spec bexpr)) AbstractFilterAttrSuppressed

abstractifyViolation :: Spec -> Term -> AbstractClause
abstractifyViolation spec bexpr = AbstractClauseFilter (abstractifyBoolTerm spec bexpr) AbstractFilterAttrViolated

abstractifyEffect :: Spec -> Effect -> AbstractClause
abstractifyEffect spec effect = case effect of
    CAll vars iexpr -> AbstractClauseEffect (abstractifyVarsAsFors spec AbstractInputAttrEnum vars (abstractifyInstListTerm spec iexpr)) AbstractEffectAttrCreate
    TAll vars iexpr -> AbstractClauseEffect (abstractifyVarsAsFors spec AbstractInputAttrEnum vars (abstractifyInstListTerm spec iexpr)) AbstractEffectAttrTerminate
    OAll vars iexpr -> AbstractClauseEffect (abstractifyVarsAsFors spec AbstractInputAttrEnum vars (abstractifyInstListTerm spec iexpr)) AbstractEffectAttrObfuscate

abstractifySyncsWith :: Spec -> Sync -> AbstractClause
abstractifySyncsWith spec (Sync vars iexpr) = AbstractClauseEffect (abstractifyVarsAsFors spec AbstractInputAttrTrigger vars (abstractifyInstListTerm spec iexpr)) AbstractEffectAttrTrigger

abstractifyTypeSpec :: Spec -> DomId -> TypeSpec -> AbstractTypeSpec
abstractifyTypeSpec spec id tyspec = AbstractTypeSpec
                                       (case (domain tyspec) of
                                           AnyString -> AbstractFieldsAtomicOpen AbstractPrimitiveTypeString
                                           AnyInt -> AbstractFieldsAtomicOpen AbstractPrimitiveTypeInt
                                           Strings dom -> AbstractFieldsAtomicClose (AbstractPrimitiveValuesString dom)
                                           Ints dom -> AbstractFieldsAtomicClose (AbstractPrimitiveValuesInt dom)
                                           -- Compiles to `Foreach <field1>: (Foreach <field2>: (<id>(<fields...>) Where <term>))
                                           Products vars -> AbstractFieldsComposite (map (abstractifyVarAsField spec) vars)
                                           -- TODO(?)
                                           Time -> throw UnsupportedTime)
                                       (S.fromList (
                                           case (domain tyspec) of
                                               AnyString -> [AbstractClauseInfinite]
                                               AnyInt -> [AbstractClauseInfinite]
                                               Strings dom -> [AbstractClauseFinite (map AbstractInstString dom)]
                                               Ints dom -> [AbstractClauseFinite (map AbstractInstInt dom)]
                                               -- Compiles to `Foreach <field1>: (Foreach <field2>: (<id>(<fields...>) Where <term>))
                                               Products _ -> [AbstractClauseInfinite]
                                               -- TODO(?)
                                               Time -> throw UnsupportedTime
                                           ++ (map (abstractifyDerivation spec id (domain tyspec)) (derivation tyspec)) ++ (map (abstractifyCondition spec) (conditions tyspec))
                                           ++ case (kind tyspec) of
                                                  Fact _ -> []
                                                  Event event -> {- [genEventHoldsWhenTrue spec id (domain tyspec)] ++ -} (map (abstractifyEffect spec) (event_effects event)) ++ ((map (abstractifySyncsWith spec) (event_syncs event)))
                                                  Act act -> [AbstractClauseAct] ++ (map (abstractifyEffect spec) (effects act)) ++ (map (abstractifySyncsWith spec) (syncs act))
                                                  Duty duty -> (map (abstractifyViolation spec) (violated_when duty))
                                       ))

-- Turns an eFLINT specification into an abstract specification as defined by the paper.
abstractifySpec :: Spec -> AbstractSpec
abstractifySpec spec = AbstractSpec (M.mapKeys preprocessTyName (M.mapWithKey (abstractifyTypeSpec spec) (decls spec)))



abstractifyTransType :: TransType -> AbstractEffectAttr
abstractifyTransType trans = case trans of
    AddEvent -> AbstractEffectAttrCreate
    RemEvent -> AbstractEffectAttrTerminate
    ObfEvent -> AbstractEffectAttrObfuscate
    Trigger -> AbstractEffectAttrTrigger

-- Turns an eFLINT statement into an abstract one.
abstractifyStatement :: Spec -> Statement -> Maybe (AbstractInstList, AbstractEffectAttr)
abstractifyStatement spec stmt = case stmt of
    Trans vars trans iexpr -> case iexpr of
        Left iexpr -> Just ((abstractifyInstListTerm spec iexpr), (abstractifyTransType trans))
        Right (ty, args) -> abstractifyStatement spec (Trans vars trans (Left (App ty args)))
    Query _ -> Nothing              -- We simply ignore them

-- Turns an eFLINT scenario into an abstract scenario as defined by the paper.
-- NOTE: Given as a list of phrase groups
abstractifyScenario :: Spec -> [[Statement]] -> AbstractScenario
abstractifyScenario spec stmts = AbstractScenario (map (\stmts -> AbstractGroup (foldl' (\list elem -> case elem of { Just elem -> list ++ [elem]; Nothing -> list }) [] (map (abstractifyStatement spec) stmts))) stmts)
