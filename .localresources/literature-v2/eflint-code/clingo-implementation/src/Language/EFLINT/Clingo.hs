module Language.EFLINT.Clingo where

-- import Language.EFLINT.Spec (Elem(..), Tagged(..))
-- import Language.EFLINT.State (Info(..), State(..))
import Language.EFLINT.Abstract(AbstractArgs(..), AbstractGroup(..), AbstractSpec(..), AbstractField(..), AbstractFields(..), AbstractScenario(..), AbstractPrimitiveType(..), AbstractTuple, AbstractPatt(..), AbstractPrimitiveValues(..), AbstractTypeSpec(..), AbstractVar(..), AbstractAggr(..), AbstractStruct(..), AbstractType(..), AbstractInstList(..), AbstractBoolBinOp(..), AbstractClause(..), AbstractBoolExpr(..), AbstractInstExpr(..), AbstractInstBinOp (..), AbstractOutputAttr(..), AbstractInputAttr(..), AbstractEffectAttr (..), AbstractAritBinOp (..), pattAsInstExpr, specAsTuples, effectAttrAsOutputAttr, filterAttrAsOutputAttr, idInAbstractClause, bumpId, tupleAsInstLists, typifyAbstractInstExpr)
import Language.EFLINT.Options(Options(..), OptionsStruct(..))

import Control.Exception(Exception, throw)
import Data.List(foldl', intersperse)
import qualified Data.Map as M
import qualified Data.Set as S
import Data.Data (Typeable)
import Debug.Trace(trace)
import Data.IORef (readIORef)
import System.IO.Unsafe (unsafePerformIO)


dbg = flip trace


----- ERRORS -----
data CompileException = UnexpectedNestedNeg
                      | UnexpectedProj
                      | UndefinedType String String         -- what, ty
                      | NotYetImplemented
                      | UnassignedVariable String
                      | FieldNotGiven AbstractType AbstractField [AbstractField]
                      | StringLitInAritExpr
                      | AggregatorWithoutFor AbstractInstList
                      | UnsupportedAbstractInstListWithOutputAttrOnTuple
                      deriving (Show, Typeable)
instance Exception CompileException

type VarAssign = M.Map String (String, Maybe [String])
type VarAssignInternal = [(String, (String, Maybe [String]))]





----- DATA -----
-- Configures the compilation.
data ClingoConfig = ClingoConfig {
                        show_libs :: Bool
                    }
                  deriving (Eq, Ord, Show, Read)

fromOptions :: Options -> ClingoConfig
fromOptions opts = ClingoConfig (not (unsafePerformIO (clingo_no_libs <$> readIORef opts))) {- (unsafePerformIO (clingo_pretty <$> readIORef opts)) -}



-- Defines possible states to generate.
data ClingoState = ClingoStateGeneric
                 | ClingoStateSpecific Int
                 deriving (Eq, Ord, Show, Read)





----- CLINGO LIBS -----
-- Creates the state trace rules for Clingo
genStateTraceLib :: String
genStateTraceLib = "state(1).\n\
                   \state(S) :- in(F, S).\n\
                   \state(S - 1) :- state(S), 1 < S.\n\
                   \:- state(S), not 0 < S.\n\
                   \in(F, S + 1) :- in((add, F), S), not in((rem, F), S), state(S + 1).\n\
                   \in((add, F), S + 1) :- in((add, F), S), not in((rem, F), S), state(S + 1).\n"
-- Creates the eFLINT semantic rules atop the state trace lib
genEFlintLib :: String
genEFlintLib = "in((add, (created, X)), S) :- in((create, X), S).\n\
               \in((rem, (terminated, X)), S) :- in((create, X), S).\n\
               \in((rem, (created, X)), S) :- in((terminate, X), S), not in((create, X), S).\n\
               \in((add, (terminated, X)), S) :- in((terminate, X), S), not in((create, X), S).\n\
               \in((rem, (created, X)), S) :- in((obfuscate, X), S), not in((terminate, X), S), not in((create, X), S).\n\
               \in((rem, (terminated, X)), S) :- in((obfuscate, X), S), not in((terminate, X), S), not in((create, X), S).\n"
               ++ "in((holds, X), S) :- in((created, X), S).\n\
                  \in((holds, X), S) :- in((derived, X), S), not in((suppressed, X), S), not in((terminated, X), S).\n\
                  \in((enabled, X), S) :- in((holds, X), S), not in((suppressed, X), S).\n"
               ++ "in((dutyViolation, X), S) :- in((violated, X), S), in((enabled, X), S).\n\
                  \in((actViolation, X), S) :- in((actTrigger, X), S), not in((enabled, X), S).\n"





----- STAGE 2: COMPILATION -----
-- genEnumTy :: AbstractType -> String
-- genEnumTy (AbstractTypeString ty) = ty
-- genEnumTy (AbstractTypeInt ty) = show ty

-- genEnumValue :: AbstractType -> String -> String
-- genEnumValue ty val = "in(enum(" ++ (genEnumTy ty) ++ "(" ++ val ++ ")), S)."

-- genFieldVars :: [AbstractField] -> String -> String
-- genFieldVars [] _ = ""
-- genFieldVars (_:[]) id = id
-- genFieldVars (_:vars) id = id ++ ", " ++ (genFieldVars vars (bumpId id))

-- genEnum :: AbstractType -> AbstractTypeSpec -> String
-- genEnum ty (AbstractTypeSpec fields clauses) = case fields of
--                                                    (AbstractFieldsAtomicOpen AbstractPrimitiveTypeString) -> "in(enum(" ++ (genEnumTy ty) ++ "(X)), S) :- in(holds(" ++ (genEnumTy ty) ++ "(X)), S).\n"
--                                                    (AbstractFieldsAtomicOpen AbstractPrimitiveTypeInt) -> "in(enum(" ++ (genEnumTy ty) ++ "(X)), S) :- in(holds(" ++ (genEnumTy ty) ++ "(X)), S).\n"
--                                                    (AbstractFieldsAtomicClose (AbstractPrimitiveValuesString dom)) -> foldl' (++) "" (intersperse " " (map (genEnumValue ty) dom)) ++ "\n"
--                                                    (AbstractFieldsAtomicClose (AbstractPrimitiveValuesInt dom)) -> foldl' (++) "" (intersperse " " (map ((genEnumValue ty) . show) dom)) ++ "\n"
--                                                    (AbstractFieldsComposite fields) -> "in(enum(" ++ (genEnumTy ty) ++ "(" ++ (genFieldVars fields "A") ++ ")), S) :- in(holds(" ++ (genEnumTy ty) ++ "(" ++ (genFieldVars fields "A") ++ ")), S).\n"

-- -- Generates enum expressions for various types in a spec
-- genEnums :: AbstractSpec -> String
-- genEnums (AbstractSpec tys) = M.foldl' (++) "" (M.mapWithKey genEnum tys)



-- Switcheroos the operators in an aggregated expressions around s.t. Clingo is happy again.
replaceOps :: String -> String
replaceOps "" = ""
replaceOps (';':rem) = "," ++ (replaceOps rem)
replaceOps (':':'-':rem) = ":" ++ (replaceOps rem)
replaceOps (c:rem) = [c] ++ (replaceOps rem)



idInAssignments :: VarAssignInternal -> String -> Bool
idInAssignments [] id = False
idInAssignments ((_, (var, Nothing)):assign) id = var == id || (idInAssignments assign id)
idInAssignments ((_, (_, Just args)):assign) id = (foldl' (||) False (map ((==) id) args)) || (idInAssignments assign id)

uniquifyAssignmentArgs :: AbstractClause -> VarAssignInternal -> [String] -> [String] -> [String]
uniquifyAssignmentArgs clause assign unique [] = unique
uniquifyAssignmentArgs clause assign unique (arg:args) = if ((idInAbstractClause arg clause) || (idInAssignments assign arg) || (elem arg unique))
                                                             then uniquifyAssignmentArgs clause assign unique ([bumpId arg] ++ args)
                                                             else uniquifyAssignmentArgs clause assign ([arg] ++ unique) args
 
uniquifyAssignments :: AbstractSpec -> AbstractClause -> VarAssignInternal -> VarAssignInternal -> VarAssignInternal
uniquifyAssignments _ clause unique [] = unique
uniquifyAssignments spec clause unique (head@(key, (var, Nothing)):rem) = if ((idInAbstractClause var clause) || (idInAssignments unique var))
                                                                              then uniquifyAssignments spec clause unique ([(key, (bumpId var, Nothing))] ++ rem)
                                                                              else uniquifyAssignments spec clause ([head] ++ unique) rem
uniquifyAssignments spec@(AbstractSpec tys) clause unique ((key, (ty, Just _)):rem) = case (M.lookup ty tys) of
    Just (AbstractTypeSpec fields _) -> case fields of
        AbstractFieldsAtomicOpen _ -> uniquifyAssignments spec clause ([(key, (ty, Just (uniquifyAssignmentArgs clause unique [] ["A"])))] ++ unique) rem
        AbstractFieldsAtomicClose _ -> uniquifyAssignments spec clause ([(key, (ty, Just (uniquifyAssignmentArgs clause unique [] ["A"])))] ++ unique) rem
        AbstractFieldsComposite fields -> uniquifyAssignments spec clause ([(key, (ty, Just (uniquifyAssignmentArgs clause unique [] (take (length fields) (repeat "A")))))] ++ unique) rem
    Nothing -> throw (UndefinedType "assign" ty)

-- Core of the assign algorithm which merges two list of assignments such that all variables are unique in both the clause and internally.
mergeAssignments :: AbstractSpec -> AbstractClause -> VarAssignInternal -> VarAssignInternal -> VarAssignInternal
mergeAssignments spec clause lhs rhs = uniquifyAssignments spec clause [] ((M.toList (M.fromList lhs)) ++ (M.toList (M.fromList rhs)))

assignVarsInArgs :: AbstractSpec -> AbstractClause -> AbstractArgs -> VarAssignInternal
assignVarsInArgs spec clause args = case args of
    AbstractArgsPrimitive iexpr -> assignVarsInInstExpr spec clause iexpr
    AbstractArgsComposite args -> foldl' (mergeAssignments spec clause) [] (map (\(_, iexpr) -> assignVarsInInstExpr spec clause iexpr) args)

assignVarsInBoolExpr :: AbstractSpec -> AbstractClause -> AbstractBoolExpr -> VarAssignInternal
assignVarsInBoolExpr spec clause bexpr = case bexpr of
    AbstractBoolExprTrue -> []
    AbstractBoolExprNeg bexpr -> assignVarsInBoolExpr spec clause bexpr
    AbstractBoolExprCheck _ iexpr -> assignVarsInInstExpr spec clause iexpr
    AbstractBoolExprBoolBinOp _ lhs rhs -> mergeAssignments spec clause (assignVarsInBoolExpr spec clause lhs) (assignVarsInBoolExpr spec clause rhs)
    AbstractBoolExprInstBinOp _ lhs rhs -> mergeAssignments spec clause (assignVarsInInstExpr spec clause lhs) (assignVarsInInstExpr spec clause rhs)

assignVarsInInstExpr :: AbstractSpec -> AbstractClause -> AbstractInstExpr -> VarAssignInternal
assignVarsInInstExpr spec clause iexpr = case iexpr of
    AbstractInstExprInt _ -> []
    AbstractInstExprString _ -> []
    AbstractInstExprVar (AbstractVar name ty) -> case ty of
        AbstractTypeString -> [(name, ("A", Nothing))]
        AbstractTypeInt -> [(name, ("A", Nothing))]
        AbstractTypeFunc ty -> [(name, (ty, Just []))]
    AbstractInstExprProj iexpr _ -> assignVarsInInstExpr spec clause iexpr
    AbstractInstExprStruct (AbstractStruct _ args) -> assignVarsInArgs spec clause args
    AbstractInstExprBinOp _ lhs rhs -> mergeAssignments spec clause (assignVarsInInstExpr spec clause lhs) (assignVarsInInstExpr spec clause rhs)
    AbstractInstExprAggr _ list -> assignVarsInInstList spec clause list

assignVarsInInstList :: AbstractSpec -> AbstractClause -> AbstractInstList -> VarAssignInternal
assignVarsInInstList spec clause list = case list of
    AbstractInstListFor _ patt list -> mergeAssignments spec clause (assignVarsInInstExpr spec clause (pattAsInstExpr patt)) (assignVarsInInstList spec clause list)
    AbstractInstListLet patt iexpr list -> mergeAssignments spec clause (mergeAssignments spec clause (assignVarsInInstExpr spec clause (pattAsInstExpr patt)) (assignVarsInInstExpr spec clause iexpr)) (assignVarsInInstList spec clause list)
    AbstractInstListWhere list bexpr -> mergeAssignments spec clause (assignVarsInInstList spec clause list) (assignVarsInBoolExpr spec clause bexpr)
    AbstractInstListExpr iexpr -> assignVarsInInstExpr spec clause iexpr
    AbstractInstListTuple iexprs -> foldl' (mergeAssignments spec clause) [] (map (assignVarsInInstExpr spec clause) iexprs)

assignVarsInClause :: AbstractSpec -> AbstractClause -> VarAssignInternal
assignVarsInClause spec clause = case clause of
    AbstractClauseDerive list -> assignVarsInInstList spec clause list
    AbstractClauseEffect list _ -> assignVarsInInstList spec clause list
    AbstractClauseFilter bexpr _ -> assignVarsInBoolExpr spec clause bexpr
    AbstractClauseInfinite -> []
    AbstractClauseFinite _ -> []    -- Also no variables here
    AbstractClauseAct -> []

-- Generates variable assignments for the Clingo clause
assignVars :: AbstractSpec -> AbstractClause -> VarAssign
assignVars spec clause = M.fromList (assignVarsInClause spec clause)

-- Generates variable assignments for the Clingo clause and some additionally generated phrase
assignVarsWithLists :: AbstractSpec -> AbstractClause -> [AbstractInstList] -> VarAssign
assignVarsWithLists spec clause lists = M.fromList (foldl' ((\spec clause unique list -> mergeAssignments spec clause unique (assignVarsInInstList spec clause list)) spec clause) (assignVarsInClause spec clause) lists)



-- Translates a type to Clingo
clingofyAbstractType :: AbstractType -> String
clingofyAbstractType ty = case ty of
    AbstractTypeString -> "_string"
    AbstractTypeInt -> "_int"
    AbstractTypeFunc func -> func

-- Translates a clause effect to Clingo
clingofyAbstractOutputAttr :: AbstractOutputAttr -> String
clingofyAbstractOutputAttr effect = case effect of
    AbstractOutputAttrEnum -> "enum"
    AbstractOutputAttrAct -> "actTrigger"
    AbstractOutputAttrDerived -> "derived"
    AbstractOutputAttrCreate -> "create"
    AbstractOutputAttrTerminate -> "terminate"
    AbstractOutputAttrObfuscate -> "obfuscate"
    AbstractOutputAttrTrigger -> "trigger"
    AbstractOutputAttrSuppressed -> "suppressed"
    AbstractOutputAttrViolated -> "violated"

-- Translates the generalized input attribute to Clingo
clingofyAbstractInputAttr :: AbstractInputAttr -> String
clingofyAbstractInputAttr attr = case attr of
    AbstractInputAttrEnum -> "enum"
    AbstractInputAttrHolds -> "holds"
    AbstractInputAttrEnabled -> "enabled"
    AbstractInputAttrViolated -> "violated"
    AbstractInputAttrTrigger -> "trigger"
    AbstractInputAttrActTrigger -> "actTrigger"

-- Translates aggregator functions into Clingo
clingofyAbstractAggr :: AbstractAggr -> String
clingofyAbstractAggr aggr = case aggr of
    AbstractAggrCount -> "#count"
    AbstractAggrSum -> "#sum"
    AbstractAggrMin -> "#min"
    AbstractAggrMax -> "#max"

-- Translates either a generic or specific state to Clingo (string).
clingofyClingoState :: ClingoState -> String
clingofyClingoState state = case state of
    ClingoStateGeneric -> "S"
    ClingoStateSpecific state -> show state



-- Odd helper function that takes a pattern and returns all variables in it.
findVarsInPatt :: AbstractPatt -> S.Set AbstractVar
findVarsInPatt patt = case patt of
    AbstractPattString _ -> S.empty
    AbstractPattInt _ -> S.empty
    AbstractPattVar var -> S.singleton var
    -- SUrprise! We don't recurse into structs. This because we're only interested in keeping variables that are LOCAL to the aggregator
    -- AbstractPattStruct (AbstractStruct _ args) -> case args of
    --     AbstractArgsPrimitive iexpr -> findVarsInPatt (instExprAsPatt iexpr)
    --     AbstractArgsComposite args -> foldl' S.union S.empty (map (findVarsInPatt . instExprAsPatt . snd) args)
    AbstractPattStruct _ -> S.empty

-- Odd helper function that translates the "final" instance expression in a list with a pattern
-- that guarantees that all generated instances are unique (for use in `#count`s).
replaceInstExprInListWithPatt :: S.Set AbstractVar -> AbstractInstList -> AbstractInstList
replaceInstExprInListWithPatt patts list = case list of
    AbstractInstListFor attr vars list -> AbstractInstListFor attr vars (replaceInstExprInListWithPatt (S.union patts (findVarsInPatt vars)) list)
    AbstractInstListLet patt iexpr list -> AbstractInstListLet patt iexpr (replaceInstExprInListWithPatt (S.union patts (findVarsInPatt patt)) list)
    AbstractInstListWhere list bexpr -> AbstractInstListWhere (replaceInstExprInListWithPatt patts list) bexpr
    AbstractInstListExpr _ -> AbstractInstListTuple (map AbstractInstExprVar (S.toList patts))
    AbstractInstListTuple _ -> AbstractInstListTuple (map AbstractInstExprVar (S.toList patts))

-- Translates aggregator instance expressions into Clingo.
clingofyAbstractAggrExpr :: AbstractSpec -> VarAssign -> ClingoState -> AbstractAggr -> AbstractInstList -> String
clingofyAbstractAggrExpr spec assign state aggr list = case aggr of
    -- This is a bit ugly, but to inject the tuple at the instance position of the aggregator, we have to "unwrap" the serialization of the for all the way until it's a `Where` already
    -- I.e., pretend we've already gone thru these rewrite rules:
    -- clingofyAbstractInstList spec assign state (AbstractInstListWhere list (AbstractBoolExprCheck attr (pattAsInstExpr patt))) mod
    -- (clingofyAbstractInstList spec assign state list mod) ++ " ; " ++ (clingofyAbstractBoolExpr spec assign state bexpr)
    AbstractAggrCount -> "#count{ " ++ (replaceOps (clingofyAbstractInstList spec assign state (replaceInstExprInListWithPatt S.empty list) Nothing)) ++ " }"
    _ -> (clingofyAbstractAggr aggr) ++ "{ " ++ (replaceOps (clingofyAbstractAritInstList spec assign state list Nothing)) ++ " }"

-- Translates instance expressions into Clingo in the context or arithmetic operators
clingofyAbstractAritExpr :: AbstractSpec -> VarAssign -> ClingoState -> AbstractInstExpr -> String
clingofyAbstractAritExpr spec@(AbstractSpec tys) assign state iexpr = case iexpr of
    -- Note: struct arguments are normal instances again!
    AbstractInstExprStruct (AbstractStruct ty args) -> case args of
        AbstractArgsPrimitive iexpr -> clingofyAbstractAritExpr spec assign state iexpr
        AbstractArgsComposite args -> ty ++ "(" ++ (foldl' (++) "" (intersperse ", " (map (\(_, value) -> value) (map (\(field, iexpr) -> (field, clingofyAbstractInstExpr spec assign state iexpr)) args)))) ++ ")"
    AbstractInstExprAggr aggr list -> clingofyAbstractAggrExpr spec assign state aggr list
    AbstractInstExprBinOp op lhs rhs -> do let clhs = (clingofyAbstractAritExpr spec assign state lhs)
                                           let crhs = (clingofyAbstractAritExpr spec assign state rhs)
                                           case op of
                                               AbstractAritBinOpAdd -> "(" ++ clhs ++ " + " ++ crhs ++ ")"
                                               AbstractAritBinOpSub -> "(" ++ clhs ++ " - " ++ crhs ++ ")"
                                               AbstractAritBinOpMul -> "(" ++ clhs ++ " * " ++ crhs ++ ")"
                                               AbstractAritBinOpDiv -> "(" ++ clhs ++ " / " ++ crhs ++ ")"
                                               AbstractAritBinOpRem -> "(" ++ clhs ++ " % " ++ crhs ++ ")"
    AbstractInstExprInt num -> show num
    AbstractInstExprVar (AbstractVar name _) -> case (M.lookup name assign) of
        Just (name, Just fields) -> case (M.lookup name tys) of 
            Just (AbstractTypeSpec tyfields _) -> case tyfields of
                AbstractFieldsAtomicOpen AbstractPrimitiveTypeString -> (head fields)
                AbstractFieldsAtomicOpen AbstractPrimitiveTypeInt -> (head fields)
                AbstractFieldsAtomicClose (AbstractPrimitiveValuesString _) -> (head fields)
                AbstractFieldsAtomicClose (AbstractPrimitiveValuesInt _) -> (head fields)
                AbstractFieldsComposite _ -> name ++ "(" ++ (foldl' (++) "" (intersperse ", " fields)) ++ ")"
            Nothing -> throw (UndefinedType "aritexpr" name)
        Just (name, Nothing) -> name
        Nothing -> throw (UnassignedVariable name)
    AbstractInstExprString string -> "\"" ++ string ++ "\""
    AbstractInstExprProj _ _ -> throw UnexpectedProj

-- Translates instance expressions into Clingo
clingofyAbstractInstExpr :: AbstractSpec -> VarAssign -> ClingoState -> AbstractInstExpr -> String
clingofyAbstractInstExpr spec assign state iexpr = case iexpr of
    AbstractInstExprStruct (AbstractStruct ty args) -> case args of
        AbstractArgsPrimitive iexpr -> ty ++ "(" ++ (clingofyAbstractAritExpr spec assign state iexpr) ++ ")"
        AbstractArgsComposite args -> ty ++ "(" ++ (foldl' (++) "" (intersperse ", " (map (\(_, iexpr) -> clingofyAbstractInstExpr spec assign state iexpr) args))) ++ ")"
    AbstractInstExprAggr aggr list -> clingofyAbstractAggrExpr spec assign state aggr list
    AbstractInstExprBinOp _ _ _ -> (clingofyAbstractAritExpr spec assign state iexpr)
    AbstractInstExprInt num -> show num
    AbstractInstExprVar (AbstractVar name _) -> case (M.lookup name assign) of
        Just (name, Just fields) -> name ++ "(" ++ (foldl' (++) "" (intersperse ", " fields)) ++ ")"
        Just (name, Nothing) -> name
        Nothing -> throw (UnassignedVariable name)
    AbstractInstExprString string -> "\"" ++ string ++ "\""
    AbstractInstExprProj _ _ -> throw UnexpectedProj



-- Translates boolean expressions into Clingo
clingofyAbstractBoolExpr :: AbstractSpec -> VarAssign -> ClingoState -> AbstractBoolExpr -> String
clingofyAbstractBoolExpr spec assign state bexpr = case bexpr of
    AbstractBoolExprTrue -> "#true"
    AbstractBoolExprCheck attr iexpr -> "in((" ++ (clingofyAbstractInputAttr attr) ++ ", " ++ (clingofyAbstractInstExpr spec assign state iexpr) ++ "), " ++ (clingofyClingoState state) ++ ")"
    AbstractBoolExprBoolBinOp AbstractBoolBinOpConj lhs rhs -> (clingofyAbstractBoolExpr spec assign state lhs) ++ " ; " ++ (clingofyAbstractBoolExpr spec assign state rhs)
    AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj lhs (AbstractBoolExprNeg rhs) -> (clingofyAbstractBoolExpr spec assign state lhs) ++ " : " ++ (clingofyAbstractBoolExpr spec assign state rhs)
    AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj lhs rhs -> (clingofyAbstractBoolExpr spec assign state lhs) ++ " : not " ++ (clingofyAbstractBoolExpr spec assign state rhs)
    AbstractBoolExprInstBinOp AbstractInstBinOpLt lhs rhs -> (clingofyAbstractAritExpr spec assign state lhs) ++ " < " ++ (clingofyAbstractAritExpr spec assign state rhs)
    AbstractBoolExprInstBinOp AbstractInstBinOpEq lhs rhs -> case ((typifyAbstractInstExpr lhs), (typifyAbstractInstExpr rhs)) of
        -- NOTE: We do this to detect when the equality concerns an "arithmetic" use-case (i.e., primitives need to be projected into)
        (AbstractTypeString, _) -> (clingofyAbstractAritExpr spec assign state lhs) ++ " = " ++ (clingofyAbstractAritExpr spec assign state rhs)
        (AbstractTypeInt, _) -> (clingofyAbstractAritExpr spec assign state lhs) ++ " = " ++ (clingofyAbstractAritExpr spec assign state rhs)
        (_, AbstractTypeString) -> (clingofyAbstractAritExpr spec assign state lhs) ++ " = " ++ (clingofyAbstractAritExpr spec assign state rhs)
        (_, AbstractTypeInt) -> (clingofyAbstractAritExpr spec assign state lhs) ++ " = " ++ (clingofyAbstractAritExpr spec assign state rhs)
        _ -> (clingofyAbstractInstExpr spec assign state lhs) ++ " = " ++ (clingofyAbstractInstExpr spec assign state rhs)
    AbstractBoolExprNeg bexpr -> "not " ++ (clingofyAbstractBoolExpr spec assign state bexpr)



-- Translates instance lists into Clingo but in the context that should hopefully produce an arithmetic expression
clingofyAbstractAritInstList :: AbstractSpec -> VarAssign -> ClingoState -> AbstractInstList -> Maybe AbstractOutputAttr -> String
clingofyAbstractAritInstList spec assign state clause mod = case clause of
    AbstractInstListFor attr patt list -> clingofyAbstractAritInstList spec assign state (AbstractInstListWhere list (AbstractBoolExprCheck attr (pattAsInstExpr patt))) mod
    AbstractInstListWhere list bexpr -> (clingofyAbstractAritInstList spec assign state list mod) ++ " ; " ++ (clingofyAbstractBoolExpr spec assign state bexpr)
    AbstractInstListLet patt iexpr list -> (clingofyAbstractAritInstList spec assign state list mod) ++ " ; " ++ (clingofyAbstractInstExpr spec assign state (pattAsInstExpr patt)) ++ " = " ++ (clingofyAbstractInstExpr spec assign state iexpr)
    AbstractInstListExpr iexpr -> case mod of
        Just mod -> "in((" ++ (clingofyAbstractOutputAttr mod) ++ ", " ++ (clingofyAbstractAritExpr spec assign state iexpr) ++ "), " ++ (clingofyClingoState state) ++ ") :- state(S)"
        Nothing -> (clingofyAbstractAritExpr spec assign state iexpr) ++ " :- #true"
    AbstractInstListTuple iexprs -> foldl' (++) "" (intersperse ", " (map (clingofyAbstractAritExpr spec assign state) iexprs))

-- Translates instance lists into Clingo
clingofyAbstractInstList :: AbstractSpec -> VarAssign -> ClingoState -> AbstractInstList -> Maybe AbstractOutputAttr -> String
clingofyAbstractInstList spec assign state clause mod = case clause of
    AbstractInstListFor attr patt list -> clingofyAbstractInstList spec assign state (AbstractInstListWhere list (AbstractBoolExprCheck attr (pattAsInstExpr patt))) mod
    AbstractInstListWhere list bexpr -> (clingofyAbstractInstList spec assign state list mod) ++ " ; " ++ (clingofyAbstractBoolExpr spec assign state bexpr)
    AbstractInstListLet patt iexpr list -> (clingofyAbstractInstList spec assign state list mod) ++ " ; " ++ (clingofyAbstractInstExpr spec assign state (pattAsInstExpr patt)) ++ " = " ++ (clingofyAbstractInstExpr spec assign state iexpr)
    AbstractInstListExpr iexpr -> case mod of
        Just mod -> "in((" ++ (clingofyAbstractOutputAttr mod) ++ ", " ++ (clingofyAbstractInstExpr spec assign state iexpr) ++ "), " ++ (clingofyClingoState state) ++ ") :- state(S)"
        Nothing -> (clingofyAbstractInstExpr spec assign state iexpr) ++ " :- #true"
    AbstractInstListTuple iexprs -> case mod of
        Just _ -> throw UnsupportedAbstractInstListWithOutputAttrOnTuple
        Nothing -> (foldl' (++) "" (intersperse ", " (map (clingofyAbstractInstExpr spec assign state) iexprs))) ++ " :- #true"



-- Translates tuples (as per the paper) into Clingo rules.
clingofyAbstractTuple :: AbstractTuple -> String
clingofyAbstractTuple tuple@(spec, ty, clause) = case clause of
    AbstractClauseDerive _ -> do let lists = tupleAsInstLists tuple
                                 foldl' (++) "" (map ((\spec clause list -> (clingofyAbstractInstList spec (assignVarsWithLists spec clause lists) ClingoStateGeneric list (Just AbstractOutputAttrDerived)) ++ ".\n") spec clause) lists)
    AbstractClauseEffect _ effect -> do let lists = tupleAsInstLists tuple
                                        foldl' (++) "" (map ((\spec clause list -> (clingofyAbstractInstList spec (assignVarsWithLists spec clause lists) ClingoStateGeneric list (Just (effectAttrAsOutputAttr effect))) ++ ".\n") spec clause) lists)
    AbstractClauseFilter _ filter -> do let lists = tupleAsInstLists tuple
                                        foldl' (++) "" (map ((\spec clause list -> (clingofyAbstractInstList spec (assignVarsWithLists spec clause lists) ClingoStateGeneric list (Just (filterAttrAsOutputAttr filter))) ++ ".\n") spec clause) lists)
    AbstractClauseInfinite -> do let lists = tupleAsInstLists tuple
                                 foldl' (++) "" (map ((\spec clause list -> (clingofyAbstractInstList spec (assignVarsWithLists spec clause lists) ClingoStateGeneric list (Just AbstractOutputAttrEnum)) ++ ".\n") spec clause) lists)
    AbstractClauseFinite insts -> do let lists = tupleAsInstLists tuple
                                     foldl' (++) "" (map ((\spec clause list -> (clingofyAbstractInstList spec (assignVarsWithLists spec clause lists) ClingoStateGeneric list (Just AbstractOutputAttrEnum)) ++ ".\n") spec clause) lists)
    AbstractClauseAct -> do let lists = tupleAsInstLists tuple
                            foldl' (++) "" (map ((\spec clause list -> (clingofyAbstractInstList spec (assignVarsWithLists spec clause lists) ClingoStateGeneric list (Just AbstractOutputAttrAct)) ++ ".\n") spec clause) lists)

-- Translates specifications into fragments of Clingo
clingofyAbstractSpec :: ClingoConfig -> AbstractSpec -> String
clingofyAbstractSpec cfg spec = (if (show_libs cfg)
                                    then genStateTraceLib ++ "\n" ++ genEFlintLib ++ "\n"
                                    else "") ++ (foldl' (++) "" (map clingofyAbstractTuple (specAsTuples spec)))



-- -- Translates an eFLINT `Tagged` into Clingo.
-- clingofyTagged :: Tagged -> String
-- clingofyTagged (args, ty) = case args of
--     Language.EFLINT.Spec.String value -> ty ++ "(\"" ++ value ++ "\")"
--     Language.EFLINT.Spec.Int value -> ty ++ "(\"" ++ (show value) ++ "\")"
--     Language.EFLINT.Spec.Product values -> ty ++ "(" ++ (foldl' (++) "" (intersperse ", " (map clingofyTagged values))) ++ ")"

-- -- Translates a type identifier and an Info describing its state into a Clingo update.
-- clingofyInstState :: Tagged -> Info -> String
-- clingofyInstState inst info = case (from_sat info) of
--     False -> "in(" ++ (if (value info) then "create" else "terminate") ++ "(" ++ (clingofyTagged inst) ++ "), " ++ (clingofyClingoState (ClingoStateSpecific 1)) ++ ") :- #true.\n"
--     True -> ""      -- Skip if it's derived (let Clingo do that)

-- -- Translates an eFLINT state into a series of Clingo triggers for the current state.
-- clingofyState :: State -> String
-- clingofyState state = M.foldlWithKey' ((\i snippet inst info -> snippet ++ (clingofyInstState inst info)) (time state)) "" (contents state)



clingofyEnumeratedAbstractClause :: AbstractSpec -> String -> (Int, (AbstractInstList, AbstractEffectAttr)) -> String
clingofyEnumeratedAbstractClause spec snippet (i, (list, effect)) = do let assign = assignVars spec (AbstractClauseEffect list effect)
                                                                       snippet ++ (clingofyAbstractInstList spec assign (ClingoStateSpecific i) list (Just (effectAttrAsOutputAttr effect))) ++ ".\n"

clingofyEnumeratedAbstractGroup :: AbstractSpec -> String -> (Int, AbstractGroup) -> String
clingofyEnumeratedAbstractGroup spec snippet (i, (AbstractGroup effects)) = foldl' (clingofyEnumeratedAbstractClause spec) snippet (map (\effect -> (i, effect)) effects)

-- Translates scenarios into fragments of Clingo
clingofyAbstractScenario :: AbstractSpec -> AbstractScenario -> String
clingofyAbstractScenario spec (AbstractScenario groups) = ("state(" ++ (show (1 + (length groups))) ++ ").\n") ++ foldl' (clingofyEnumeratedAbstractGroup spec) "" (zip [1..] groups)
