module Language.EFLINT.Normalize where

import Language.EFLINT.Abstract(AbstractAggr(..), AbstractArgs(..), AbstractBoolBinOp(..), AbstractBoolExpr(..), AbstractClause(..), AbstractField(..), AbstractFields(..), AbstractGroup(..), AbstractInputAttr(..), AbstractInstExpr(..), AbstractInstList(..), AbstractPatt(..), AbstractScenario(..), AbstractSpec(..), AbstractStruct(..), AbstractType(..), AbstractTypeSpec(..), AbstractVar(..), bumpIdLowercase, {- fieldAsVar, -} fieldPattUnique, genUniqueIdInContext, instAsInstExpr, instExprAsInst, instExprAsPatt, pattAsInstExpr, varAsField)
-- import Language.EFLINT.Abstract(trace_show)
-- import Language.EFLINT.Abstract(ppAbstractInstExpr)

import Control.Exception(Exception, throw)
import Data.Data (Typeable)
import Data.List (foldl')
-- import Debug.Trace(trace)
-- import Debug.Trace
import qualified Data.Map as M
import qualified Data.Set as S


----- HELPERS -----
-- Generates a unique instance ID in the given spec.
genUniqueInstId :: AbstractSpec -> String
genUniqueInstId spec = genUniqueInstIdInner spec "a"
                       where genUniqueInstIdInner (AbstractSpec tys) id = case (M.lookup id tys) of
                                                                              Just _ -> genUniqueInstIdInner spec (bumpIdLowercase id)
                                                                              Nothing -> id
                                                                        
-- Returns an identifier that is guaranteed to be unique among variables in the given spec _and_ additional list of identifiers.
genUniqueInstIdInContext :: AbstractSpec -> [String] -> String -> String
genUniqueInstIdInContext spec@(AbstractSpec tys) context id = case (M.lookup id tys) of
    Just _ -> genUniqueInstIdInContext spec context (bumpIdLowercase id)
    Nothing -> if elem id context
                   then genUniqueInstIdInContext spec context (bumpIdLowercase id)
                   else id




----- TRAVERSALS: DEPROJ -----
data ProjException = IllegalProjectedInstance AbstractInstExpr
                   | UnknownField String AbstractField
                   | UnwrappingPrimitiveVar AbstractVar
                   | UnsupportedInstListAggrExpression AbstractInstList
                   deriving(Show, Typeable)
instance Exception ProjException



data DeprojResult a = Gucci a
                    | Goofy AbstractVar
                    deriving(Eq, Read, Show)

keys :: [(a, b)] -> [a]
keys [] = []
keys ((a, _):rem) = [a] ++ (keys rem)

elems :: [(a, b)] -> [b]
elems [] = []
elems ((_, b):rem) = [b] ++ (elems rem)

chainResult :: DeprojResult a -> DeprojResult b -> DeprojResult (a, b)
chainResult lhs rhs = case lhs of
    Gucci lhs -> case rhs of
        Gucci rhs -> Gucci (lhs, rhs)
        Goofy var -> Goofy var
    Goofy var -> Goofy var
chainLResult :: DeprojResult a -> DeprojResult a -> DeprojResult [a]
chainLResult lhs rhs = case lhs of
    Gucci lhs -> case rhs of
        Gucci rhs -> Gucci [lhs, rhs]
        Goofy var -> Goofy var
    Goofy var -> Goofy var

mapResult :: (a -> b) -> DeprojResult a -> DeprojResult b
mapResult closure res = case res of
    Gucci ty -> Gucci (closure ty)
    Goofy var -> Goofy var

fmapResult :: (a -> DeprojResult b) -> DeprojResult a -> DeprojResult b
fmapResult closure res = case res of
    Gucci ty -> case (closure ty) of
        Gucci ty -> Gucci ty
        Goofy var -> Goofy var
    Goofy var -> Goofy var

flipResult :: [DeprojResult a] -> DeprojResult [a]
flipResult [] = Gucci []
flipResult (res:rem) = case res of
    Gucci res -> mapResult ((\res list -> [res] ++ list) res) (flipResult rem)
    Goofy var -> Goofy var
flipMResult :: Ord(a) => [(a, DeprojResult b)] -> DeprojResult [(a, b)]
flipMResult m = mapResult (zip (keys m)) (flipResult (elems m))



degooflifyAbstractArgs :: AbstractVar -> AbstractPatt -> AbstractArgs -> AbstractArgs
degooflifyAbstractArgs replacevar replacepatt args = case args of
    AbstractArgsPrimitive iexpr -> AbstractArgsPrimitive (degooflifyAbstractInstExpr replacevar replacepatt iexpr)
    AbstractArgsComposite args -> AbstractArgsComposite (map (\(field, iexpr) -> (field, degooflifyAbstractInstExpr replacevar replacepatt iexpr)) args)

degooflifyAbstractBoolExpr :: AbstractVar -> AbstractPatt -> AbstractBoolExpr -> AbstractBoolExpr
degooflifyAbstractBoolExpr replacevar replacepatt bexpr = case bexpr of
    AbstractBoolExprTrue -> bexpr
    AbstractBoolExprNeg bexpr -> AbstractBoolExprNeg (degooflifyAbstractBoolExpr replacevar replacepatt bexpr)
    AbstractBoolExprCheck attr iexpr -> AbstractBoolExprCheck attr (degooflifyAbstractInstExpr replacevar replacepatt iexpr)
    AbstractBoolExprBoolBinOp op lhs rhs -> AbstractBoolExprBoolBinOp op (degooflifyAbstractBoolExpr replacevar replacepatt lhs) (degooflifyAbstractBoolExpr replacevar replacepatt rhs)
    AbstractBoolExprInstBinOp op lhs rhs -> AbstractBoolExprInstBinOp op (degooflifyAbstractInstExpr replacevar replacepatt lhs) (degooflifyAbstractInstExpr replacevar replacepatt rhs)

degooflifyAbstractInstExpr :: AbstractVar -> AbstractPatt -> AbstractInstExpr -> AbstractInstExpr
degooflifyAbstractInstExpr replacevar replacepatt iexpr = case iexpr of
    AbstractInstExprString _ -> iexpr
    AbstractInstExprInt _ -> iexpr
    AbstractInstExprVar var -> case var == replacevar of
        True -> pattAsInstExpr replacepatt
        False -> iexpr
    AbstractInstExprStruct (AbstractStruct ty args) -> AbstractInstExprStruct (AbstractStruct ty (degooflifyAbstractArgs replacevar replacepatt args))
    AbstractInstExprProj iexpr field -> AbstractInstExprProj (degooflifyAbstractInstExpr replacevar replacepatt iexpr) field
    AbstractInstExprBinOp op lhs rhs -> AbstractInstExprBinOp op (degooflifyAbstractInstExpr replacevar replacepatt lhs) (degooflifyAbstractInstExpr replacevar replacepatt rhs)
    AbstractInstExprAggr aggr list -> AbstractInstExprAggr aggr (degooflifyAbstractInstList replacevar replacepatt list)

degooflifyAbstractInstList :: AbstractVar -> AbstractPatt -> AbstractInstList -> AbstractInstList
degooflifyAbstractInstList replacevar replacepatt list = case list of
    AbstractInstListFor attr patt list -> AbstractInstListFor attr (instExprAsPatt (degooflifyAbstractInstExpr replacevar replacepatt (pattAsInstExpr patt))) (degooflifyAbstractInstList replacevar replacepatt list)
    AbstractInstListLet patt iexpr list -> AbstractInstListLet (instExprAsPatt (degooflifyAbstractInstExpr replacevar replacepatt (pattAsInstExpr patt))) (degooflifyAbstractInstExpr replacevar replacepatt iexpr) (degooflifyAbstractInstList replacevar replacepatt list)
    AbstractInstListWhere list bexpr -> AbstractInstListWhere (degooflifyAbstractInstList replacevar replacepatt list) (degooflifyAbstractBoolExpr replacevar replacepatt bexpr)
    AbstractInstListExpr iexpr -> AbstractInstListExpr (degooflifyAbstractInstExpr replacevar replacepatt iexpr)
    AbstractInstListTuple iexprs -> AbstractInstListTuple (map (degooflifyAbstractInstExpr replacevar replacepatt) iexprs)



deprojTryAbstractArgs :: AbstractSpec -> AbstractArgs -> DeprojResult AbstractArgs
deprojTryAbstractArgs spec args = case args of
    AbstractArgsPrimitive iexpr -> mapResult AbstractArgsPrimitive (deprojTryAbstractInstExpr spec iexpr)
    AbstractArgsComposite args -> mapResult AbstractArgsComposite (flipMResult (map (\(field, iexpr) -> (field, deprojTryAbstractInstExpr spec iexpr)) args))

deprojTryAbstractBoolExpr :: AbstractSpec -> AbstractBoolExpr -> DeprojResult AbstractBoolExpr
deprojTryAbstractBoolExpr spec bexpr = case bexpr of
    AbstractBoolExprTrue -> Gucci AbstractBoolExprTrue
    AbstractBoolExprNeg bexpr -> mapResult AbstractBoolExprNeg (deprojTryAbstractBoolExpr spec bexpr)
    AbstractBoolExprCheck attr iexpr -> mapResult (AbstractBoolExprCheck attr) (deprojTryAbstractInstExpr spec iexpr)
    AbstractBoolExprBoolBinOp op lhs rhs -> mapResult ((\op (lhs, rhs) -> AbstractBoolExprBoolBinOp op lhs rhs) op) (chainResult (deprojTryAbstractBoolExpr spec lhs) (deprojTryAbstractBoolExpr spec rhs))
    AbstractBoolExprInstBinOp op lhs rhs -> mapResult ((\op (lhs, rhs) -> AbstractBoolExprInstBinOp op lhs rhs) op) (chainResult (deprojTryAbstractInstExpr spec lhs) (deprojTryAbstractInstExpr spec rhs))

deprojTryAbstractInstExpr :: AbstractSpec -> AbstractInstExpr -> DeprojResult AbstractInstExpr
deprojTryAbstractInstExpr spec iexpr = case iexpr of
    -- Projection!
    AbstractInstExprProj iexpr field -> case iexpr of
        -- Projection cases
        AbstractInstExprVar var -> Goofy var            -- We'll have to get rid of this first
        AbstractInstExprStruct (AbstractStruct ty args) -> case args of
            AbstractArgsPrimitive _ -> throw (IllegalProjectedInstance iexpr)
            AbstractArgsComposite args -> case (lookup field args) of
                Just niexpr -> Gucci niexpr
                Nothing -> throw (UnknownField ty field)
        AbstractInstExprProj niexpr nfield -> fmapResult ((deprojTryAbstractInstExpr spec) . ((flip AbstractInstExprProj) field)) (deprojTryAbstractInstExpr spec (AbstractInstExprProj niexpr nfield))

        -- Illegal cases
        AbstractInstExprString _ -> throw (IllegalProjectedInstance iexpr)
        AbstractInstExprInt _ -> throw (IllegalProjectedInstance iexpr)
        AbstractInstExprBinOp _ _ _ -> throw (IllegalProjectedInstance iexpr)
        AbstractInstExprAggr _ _ -> throw (IllegalProjectedInstance iexpr)

    -- Pass-through cases
    AbstractInstExprString _ -> Gucci iexpr
    AbstractInstExprInt _ -> Gucci iexpr
    AbstractInstExprVar _ -> Gucci iexpr
    AbstractInstExprStruct (AbstractStruct name args) -> mapResult AbstractInstExprStruct (mapResult (AbstractStruct name) (deprojTryAbstractArgs spec args))
    AbstractInstExprBinOp op lhs rhs -> mapResult ((\op (lhs, rhs) -> AbstractInstExprBinOp op lhs rhs) op) (chainResult (deprojTryAbstractInstExpr spec lhs) (deprojTryAbstractInstExpr spec rhs))
    AbstractInstExprAggr aggr list -> mapResult (AbstractInstExprAggr aggr) (deprojTryAbstractInstList spec list)

-- Attempts to get rid of projections in the given AbstractInstList.
deprojTryAbstractInstList :: AbstractSpec -> AbstractInstList -> DeprojResult AbstractInstList
deprojTryAbstractInstList spec list = case list of
    AbstractInstListFor attr patt list -> mapResult (AbstractInstListFor attr patt) (deprojTryAbstractInstList spec list)
    AbstractInstListLet patt iexpr list -> mapResult ((\patt (iexpr, list) -> AbstractInstListLet patt iexpr list) patt) (chainResult (deprojTryAbstractInstExpr spec iexpr) (deprojTryAbstractInstList spec list))
    AbstractInstListWhere list bexpr -> mapResult (\(list, bexpr) -> AbstractInstListWhere list bexpr) (chainResult (deprojTryAbstractInstList spec list) (deprojTryAbstractBoolExpr spec bexpr))
    AbstractInstListExpr iexpr -> mapResult AbstractInstListExpr (deprojTryAbstractInstExpr spec iexpr)
    AbstractInstListTuple iexprs -> mapResult AbstractInstListTuple (flipResult (map (deprojTryAbstractInstExpr spec) iexprs))



-- Gets rid of projections in the given AbstractBoolExpr.
deprojAbstractBoolExpr :: AbstractSpec -> AbstractClause -> AbstractBoolExpr -> AbstractBoolExpr
deprojAbstractBoolExpr spec clause bexpr = case (deprojTryAbstractBoolExpr spec bexpr) of
    Gucci bexpr -> bexpr
    Goofy (AbstractVar name (AbstractTypeFunc ty)) -> deprojAbstractBoolExpr spec clause (degooflifyAbstractBoolExpr (AbstractVar name (AbstractTypeFunc ty)) (fieldPattUnique ty spec clause) bexpr)
    Goofy var -> throw (UnwrappingPrimitiveVar var)

-- Gets rid of projections in the given AbstractInstList.
deprojAbstractInstList :: AbstractSpec -> AbstractClause -> AbstractInstList -> AbstractInstList
deprojAbstractInstList spec clause list = case (deprojTryAbstractInstList spec list) of
    Gucci list -> list
    Goofy (AbstractVar name (AbstractTypeFunc ty)) -> deprojAbstractInstList spec clause (degooflifyAbstractInstList (AbstractVar name (AbstractTypeFunc ty)) (fieldPattUnique ty spec clause) list)
    Goofy var -> throw (UnwrappingPrimitiveVar var)

-- Gets rid of projections in the expressions of a given AbstractTypeClause.
deprojAbstractClause :: AbstractSpec -> AbstractClause -> AbstractClause
deprojAbstractClause spec clause = case clause of
    AbstractClauseDerive list -> AbstractClauseDerive (deprojAbstractInstList spec clause list)
    AbstractClauseEffect list effect -> AbstractClauseEffect (deprojAbstractInstList spec clause list) effect
    AbstractClauseFilter bexpr filter -> AbstractClauseFilter (deprojAbstractBoolExpr spec clause bexpr) filter
    AbstractClauseInfinite -> AbstractClauseInfinite
    AbstractClauseFinite insts -> AbstractClauseFinite insts
    AbstractClauseAct -> AbstractClauseAct

-- Gets rid of projections in the clauses of the given AbstractTypeSpec.
deprojAbstractTypeSpec :: AbstractSpec -> AbstractTypeSpec -> AbstractTypeSpec
deprojAbstractTypeSpec spec (AbstractTypeSpec fields clauses) = AbstractTypeSpec fields (S.map (deprojAbstractClause spec) clauses)

-- Gets rid of projections in the given AbstractSpec.
deprojAbstractSpec :: AbstractSpec -> AbstractSpec
deprojAbstractSpec spec@(AbstractSpec tys) = AbstractSpec (M.map (deprojAbstractTypeSpec spec) tys)

deprojAbstractGroup :: AbstractSpec -> AbstractGroup -> AbstractGroup
deprojAbstractGroup spec (AbstractGroup effects) = (AbstractGroup (map (\(list, effect) -> (deprojAbstractInstList spec (AbstractClauseDerive list) list, effect)) effects))

-- Gets rid of projections in the given AbstractScenario.
deprojAbstractScenario :: AbstractSpec -> AbstractScenario -> AbstractScenario
deprojAbstractScenario spec (AbstractScenario groups) = AbstractScenario (map (deprojAbstractGroup spec) groups)





-- ----- TRAVERSALS: LIFT AGGREGATORS -----
-- data LiftAggrException = NonEmptyVarsAtSpec
--                        deriving(Show, Typeable)
-- instance Exception LiftAggrException



-- -- (let bindings to generate, `enums` to generate, resulting expression/w/e)
-- -- ([(Variable name, aggregator, aggregator expression)], renewed node)
-- type ListResult a = ([(String, AbstractAggr, AbstractInstList)], a)

-- mapListResult :: (a -> b) -> ListResult a -> ListResult b
-- mapListResult start (lets, res) = (lets, start res)

-- chainListResult :: (a -> b -> c) -> ListResult a -> ListResult b -> ListResult c
-- chainListResult start (lets1, res1) (lets2, res2) = (lets1 ++ lets2, start res1 res2)

-- chainListNResult :: [ListResult a] -> ListResult [a]
-- chainListNResult [] = ([], [])
-- chainListNResult ((lets1, res1):rem) = do let (lets2, res2) = (chainListNResult rem)
--                                           (lets1 ++ lets2, [res1] ++ res2)

-- chainListSResult :: Ord(a) => S.Set (ListResult a) -> ListResult (S.Set a)
-- chainListSResult input = mapListResult S.fromList (chainListNResult (S.toList input))

-- chainListMResult :: Ord(a) => M.Map a (ListResult b) -> ListResult (M.Map a b)
-- chainListMResult input = mapListResult M.fromList ((\(keys, (lets, res)) -> (lets, zip keys res)) ((\(keys, values) -> (keys, chainListNResult values)) (unzip (M.toList input))))



-- liftaggrAbstractBoolExpr :: AbstractSpec -> AbstractClause -> AbstractBoolExpr -> ListResult AbstractBoolExpr
-- liftaggrAbstractBoolExpr spec clause bexpr = case bexpr of
--     AbstractBoolExprTrue -> ([], bexpr)
--     AbstractBoolExprNeg bexpr -> mapListResult AbstractBoolExprNeg (liftaggrAbstractBoolExpr spec clause bexpr)
--     AbstractBoolExprCheck attr iexpr -> mapListResult (AbstractBoolExprCheck attr) (liftaggrAbstractInstExpr spec clause iexpr)
--     AbstractBoolExprBoolBinOp op lhs rhs -> chainListResult (AbstractBoolExprBoolBinOp op) (liftaggrAbstractBoolExpr spec clause lhs) (liftaggrAbstractBoolExpr spec clause rhs)
--     AbstractBoolExprInstBinOp op lhs rhs -> case op of
--         AbstractInstBinOpEq -> case ((typifyAbstractInstExpr lhs), (typifyAbstractInstExpr rhs)) of
--             -- NOTE: In arithmetic contexts (i.e., we are operating on literal values), we do _not_ extract the aggregators. This because it is allowed in Clingo and can produce different results.
--             (AbstractTypeString, _) -> ([], bexpr)
--             (AbstractTypeInt, _) -> ([], bexpr)
--             (_, AbstractTypeString) -> ([], bexpr)
--             (_, AbstractTypeInt) -> ([], bexpr)
--             _ -> chainListResult (AbstractBoolExprInstBinOp op) (liftaggrAbstractInstExpr spec clause lhs) (liftaggrAbstractInstExpr spec clause rhs)
--         AbstractInstBinOpLt -> ([], bexpr)          -- NOTE: In arithmetic contexts (i.e., we are operating on literal values), we do _not_ extract the aggregators. This because it is allowed in Clingo and can produce different results.

-- liftaggrAbstractInstExpr :: AbstractSpec -> AbstractClause -> AbstractInstExpr -> ListResult AbstractInstExpr
-- liftaggrAbstractInstExpr spec clause iexpr = case iexpr of
--     AbstractInstExprAggr aggr list -> (\varid -> ([(varid, aggr, list)], AbstractInstExprVar (AbstractVar varid AbstractTypeInt))) (genUniqueId clause)
--     AbstractInstExprString _ -> ([],iexpr)
--     AbstractInstExprInt _ -> ([],iexpr)
--     AbstractInstExprVar _ -> ([],iexpr)
--     AbstractInstExprProj iexpr field -> mapListResult ((flip AbstractInstExprProj) field) (liftaggrAbstractInstExpr spec clause iexpr)
--     AbstractInstExprBinOp _ _ _ -> ([], iexpr)          -- NOTE: In arithmetic contexts (i.e., we are operating on literal values), we do _not_ extract the aggregators. This because it is allowed in Clingo and can produce different results.
--     AbstractInstExprStruct (AbstractStruct ty args) -> mapListResult (AbstractInstExprStruct . (AbstractStruct ty)) (chainListNResult (map (\(field, iexpr) -> mapListResult ((\field iexpr -> (field, iexpr)) field) (liftaggrAbstractInstExpr spec clause iexpr)) args))

-- liftaggrAbstractInstList :: AbstractSpec -> AbstractClause -> AbstractInstList -> ListResult AbstractInstList
-- liftaggrAbstractInstList spec clause list = case list of
--     AbstractInstListFor attr patt list -> mapListResult (AbstractInstListFor attr patt) (liftaggrAbstractInstList spec clause list)
--     AbstractInstListLet patt iexpr list -> chainListResult (AbstractInstListLet patt) (liftaggrAbstractInstExpr spec clause iexpr) (liftaggrAbstractInstList spec clause list)
--     AbstractInstListWhere list bexpr -> chainListResult AbstractInstListWhere (liftaggrAbstractInstList spec clause list) (liftaggrAbstractBoolExpr spec clause bexpr)
--     AbstractInstListExpr iexpr -> mapListResult AbstractInstListExpr (liftaggrAbstractInstExpr spec clause iexpr)
--     AbstractInstListTuple iexprs -> mapListResult AbstractInstListTuple (chainListNResult (map (liftaggrAbstractInstExpr spec clause) iexprs))

-- liftaggrAbstractClause :: AbstractSpec -> AbstractClause -> ListResult AbstractClause
-- liftaggrAbstractClause spec clause = case clause of
--     AbstractClauseDerive list -> mapListResult AbstractClauseDerive (liftaggrAbstractInstList spec clause list)
--     AbstractClauseEffect list effect -> mapListResult ((flip AbstractClauseEffect) effect) (liftaggrAbstractInstList spec clause list)
--     AbstractClauseFilter bexpr filter -> mapListResult ((flip AbstractClauseFilter) filter) (liftaggrAbstractBoolExpr spec clause bexpr)
--     AbstractClauseInfinite -> ([], AbstractClauseInfinite)
--     AbstractClauseFinite insts -> ([], AbstractClauseFinite insts)
--     AbstractClauseAct -> ([], AbstractClauseAct)

-- processListResult :: ListResult AbstractInstList -> AbstractInstList
-- processListResult ([], list) = list
-- processListResult (((varname, aggr, iexpr):lets), list) = AbstractInstListLet (AbstractPattVar (AbstractVar varname AbstractTypeInt)) (AbstractInstExprAggr aggr iexpr) (processListResult (lets, list))
-- liftaggrAbstractTuple :: AbstractTuple -> [AbstractInstList]
-- liftaggrAbstractTuple tuple@(spec, ty, clause) = map processListResult (map (liftaggrAbstractInstList spec clause) (tupleAsInstLists tuple))





----- TRAVERSAL: CONJUNCTIVE NORMAL FORM -----
cnfTravAbstractArgs :: (AbstractBoolExpr -> AbstractBoolExpr) -> AbstractArgs -> AbstractArgs
cnfTravAbstractArgs trav args = case args of
    AbstractArgsPrimitive iexpr -> AbstractArgsPrimitive (cnfTravAbstractInstExpr trav iexpr)
    AbstractArgsComposite args -> AbstractArgsComposite (map (\(field, iexpr) -> (field, cnfTravAbstractInstExpr trav iexpr)) args)

cnfTravAbstractInstExpr :: (AbstractBoolExpr -> AbstractBoolExpr) -> AbstractInstExpr -> AbstractInstExpr
cnfTravAbstractInstExpr trav iexpr = case iexpr of
    AbstractInstExprString _ -> iexpr
    AbstractInstExprInt _ -> iexpr
    AbstractInstExprVar _ -> iexpr
    AbstractInstExprProj iexpr field -> AbstractInstExprProj (cnfTravAbstractInstExpr trav iexpr) field
    AbstractInstExprStruct (AbstractStruct ty args) -> AbstractInstExprStruct (AbstractStruct ty (cnfTravAbstractArgs trav args))
    AbstractInstExprBinOp op lhs rhs -> AbstractInstExprBinOp op (cnfTravAbstractInstExpr trav lhs) (cnfTravAbstractInstExpr trav rhs)
    AbstractInstExprAggr aggr list -> AbstractInstExprAggr aggr (cnfTravAbstractInstList trav list)

cnfTravAbstractInstList :: (AbstractBoolExpr -> AbstractBoolExpr) -> AbstractInstList -> AbstractInstList
cnfTravAbstractInstList trav list = case list of
    AbstractInstListFor attr vars list -> AbstractInstListFor attr (instExprAsPatt (cnfTravAbstractInstExpr trav (pattAsInstExpr vars))) (cnfTravAbstractInstList trav list)
    AbstractInstListLet var iexpr list -> AbstractInstListLet (instExprAsPatt (cnfTravAbstractInstExpr trav (pattAsInstExpr var))) (cnfTravAbstractInstExpr trav iexpr) (cnfTravAbstractInstList trav list)
    AbstractInstListWhere list bexpr -> AbstractInstListWhere (cnfTravAbstractInstList trav list) (trav bexpr)
    AbstractInstListExpr iexpr -> AbstractInstListExpr (cnfTravAbstractInstExpr trav iexpr)
    AbstractInstListTuple iexprs -> AbstractInstListTuple (map (cnfTravAbstractInstExpr trav) iexprs)

-- Converts a boolean expression into one in Negation Normal Form (NNF).
-- I.e., Gets rid of double negations in a boolean expression and pushes any negation down the binary operators
-- Algorithm: <https://personal.cis.strath.ac.uk/robert.atkey/cs208/converting-to-cnf.html>
nnfAbstractBoolExpr :: AbstractBoolExpr -> AbstractBoolExpr
nnfAbstractBoolExpr bexpr = case bexpr of
    -- `not not x` -> `x`
    AbstractBoolExprNeg (AbstractBoolExprNeg x) -> nnfAbstractBoolExpr x
    -- Apply DeMorgan on disjunction (`not (x V y)` -> `(not x) ^ (not y)`)
    AbstractBoolExprNeg (AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj x y) -> AbstractBoolExprBoolBinOp AbstractBoolBinOpConj (nnfAbstractBoolExpr (AbstractBoolExprNeg x)) (nnfAbstractBoolExpr (AbstractBoolExprNeg y))
    -- Apply DeMorgan on conjunction (`not (x ^ y)` -> `(not x) V (not y)`)
    AbstractBoolExprNeg (AbstractBoolExprBoolBinOp AbstractBoolBinOpConj x y) -> AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj (nnfAbstractBoolExpr (AbstractBoolExprNeg x)) (nnfAbstractBoolExpr (AbstractBoolExprNeg y))

    -- These are just passing the torch
    AbstractBoolExprTrue -> bexpr
    AbstractBoolExprCheck attr iexpr -> AbstractBoolExprCheck attr (cnfTravAbstractInstExpr nnfAbstractBoolExpr iexpr)
    AbstractBoolExprNeg bexpr -> AbstractBoolExprNeg (nnfAbstractBoolExpr bexpr)
    AbstractBoolExprBoolBinOp op lhs rhs -> AbstractBoolExprBoolBinOp op (nnfAbstractBoolExpr lhs) (nnfAbstractBoolExpr rhs)
    AbstractBoolExprInstBinOp op lhs rhs -> AbstractBoolExprInstBinOp op (cnfTravAbstractInstExpr nnfAbstractBoolExpr lhs) (cnfTravAbstractInstExpr nnfAbstractBoolExpr rhs)

-- Converts a boolean expression in NNF to CNF.
-- Algorithm: <https://personal.cis.strath.ac.uk/robert.atkey/cs208/converting-to-cnf.html>
nnfToCnfAbstractBoolExpr :: AbstractBoolExpr -> AbstractBoolExpr
nnfToCnfAbstractBoolExpr bexpr = case bexpr of
    -- Explode `x V (y ^ z)` -> `(x V y) ^ (x V z)`
    AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj x (AbstractBoolExprBoolBinOp AbstractBoolBinOpConj y z) -> AbstractBoolExprBoolBinOp AbstractBoolBinOpConj (nnfToCnfAbstractBoolExpr (AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj x y)) (nnfToCnfAbstractBoolExpr (AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj x z))
    -- Explode `(x ^ y) V z` -> `(x V z) ^ (y V z)`
    AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj (AbstractBoolExprBoolBinOp AbstractBoolBinOpConj x y) z -> AbstractBoolExprBoolBinOp AbstractBoolBinOpConj (nnfToCnfAbstractBoolExpr (AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj x z)) (nnfToCnfAbstractBoolExpr (AbstractBoolExprBoolBinOp AbstractBoolBinOpDisj y z))

    -- Not much more to do, I'm afraid
    AbstractBoolExprTrue -> bexpr
    AbstractBoolExprNeg bexpr -> AbstractBoolExprNeg (nnfToCnfAbstractBoolExpr bexpr)
    AbstractBoolExprCheck attr iexpr -> AbstractBoolExprCheck attr (cnfTravAbstractInstExpr nnfToCnfAbstractBoolExpr iexpr)
    AbstractBoolExprBoolBinOp op lhs rhs -> AbstractBoolExprBoolBinOp op (nnfToCnfAbstractBoolExpr lhs) (nnfToCnfAbstractBoolExpr rhs)
    AbstractBoolExprInstBinOp op lhs rhs -> AbstractBoolExprInstBinOp op (cnfTravAbstractInstExpr nnfToCnfAbstractBoolExpr lhs) (cnfTravAbstractInstExpr nnfToCnfAbstractBoolExpr rhs)



-- Puts a boolean expression in Conjunctive Normal Form (CNF).
-- Algorithm: <https://en.wikipedia.org/wiki/Conjunctive_normal_form#Conversion_to_CNF>
cnfAbstractBoolExpr :: AbstractBoolExpr -> AbstractBoolExpr
cnfAbstractBoolExpr bexpr = (nnfToCnfAbstractBoolExpr . nnfAbstractBoolExpr) bexpr

cnfAbstractInstExpr :: AbstractInstExpr -> AbstractInstExpr
cnfAbstractInstExpr iexpr = ((cnfTravAbstractInstExpr nnfToCnfAbstractBoolExpr) . (cnfTravAbstractInstExpr nnfAbstractBoolExpr)) iexpr

cnfAbstractInstList :: AbstractInstList -> AbstractInstList
cnfAbstractInstList list = ((cnfTravAbstractInstList nnfToCnfAbstractBoolExpr) . (cnfTravAbstractInstList nnfAbstractBoolExpr)) list

cnfAbstractClause :: AbstractClause -> AbstractClause
cnfAbstractClause clause = case clause of
    AbstractClauseDerive list -> AbstractClauseDerive (cnfAbstractInstList list)
    AbstractClauseEffect list effect -> AbstractClauseEffect (cnfAbstractInstList list) effect
    AbstractClauseFilter bexpr filter -> AbstractClauseFilter (cnfAbstractBoolExpr bexpr) filter
    AbstractClauseInfinite -> AbstractClauseInfinite
    AbstractClauseFinite insts -> AbstractClauseFinite (map (instExprAsInst . cnfAbstractInstExpr . instAsInstExpr) insts)
    AbstractClauseAct -> AbstractClauseAct

cnfAbstractTypeSpec :: AbstractTypeSpec -> AbstractTypeSpec
cnfAbstractTypeSpec (AbstractTypeSpec fields clauses) = AbstractTypeSpec fields (S.map cnfAbstractClause clauses)

-- Rewrites boolean expressions in the given spec to be in conjunctive normal form.
cnfAbstractSpec :: AbstractSpec -> AbstractSpec
cnfAbstractSpec (AbstractSpec tys) = AbstractSpec (M.map cnfAbstractTypeSpec tys)

cnfAbstractGroup :: AbstractGroup -> AbstractGroup
cnfAbstractGroup (AbstractGroup effects) = AbstractGroup (map (\(list, effect) -> (cnfAbstractInstList list, effect)) effects)

-- Rewrites boolean expressions in the given scenario to be in conjunctive normal form.
cnfAbstractScenario :: AbstractScenario -> AbstractScenario
cnfAbstractScenario (AbstractScenario groups) = AbstractScenario (map cnfAbstractGroup groups)





----- TRAVERSALS: UNNEST AGGREGATORS -----
-- Defines errors occuring when extracting aggregators
data FindFreeVarsException = UnextractAggregator AbstractAggr AbstractInstList
                           | UnprocessedVars [AbstractPatt]
                           | IllegalPrimitivePattern AbstractPatt
                           deriving(Show, Typeable)
instance Exception FindFreeVarsException

-- Defines the possible states for deciding whether to extract an aggregator.
data Safety = Safe
            | Replace
            | Nested        -- Same as replace, except it can't ever get better
            deriving (Eq, Ord, Show, Read)

-- Marks an existing `Safety` as `Safe` ~ unless it's `Nested`
makeSafe :: Safety -> Safety
makeSafe safety = case safety of
    Safe -> Safe
    Replace -> Safe
    Nested -> Nested

-- Marks an existing `Safety` as `Replace`
makeReplace :: Safety -> Safety
makeReplace safety = case safety of
    Safe -> Replace
    Replace -> Replace
    Nested -> Nested

-- Marks an existing `Safety` as `Nested`
makeNested :: Safety -> Safety
makeNested _ = Nested



-- Defines a particular result of functions that carries the information to construct new rules.
-- Given as tuples of new variable's ID, new type's ID, free variables, and the aggregator expression itself.
-- The second list keeps track of variables that've yet to be quantified over.
type ExtractResult a = ([(String, String, [AbstractVar], (AbstractAggr, AbstractInstList))], [AbstractPatt], a)

mapExtractResult :: (a -> b) -> ExtractResult a -> ExtractResult b
mapExtractResult pred (list, vars, res) = (list, vars, pred res)

joinExtractResult :: (a -> b -> c) -> ExtractResult a -> ExtractResult b -> ExtractResult c
joinExtractResult pred (llist, lvars, lres) (rlist, rvars, rres) = (llist ++ rlist, lvars ++ rvars, pred lres rres)

flipExtractResult :: [ExtractResult a] -> ExtractResult [a]
flipExtractResult [] = ([], [], [])
flipExtractResult ((hlist, hvars, hres):rem) = (\(list, vars, res) -> (hlist ++ list, hvars ++ vars, [hres] ++ res)) (flipExtractResult rem)

flipMExtractResult :: Ord a => M.Map a (ExtractResult b) -> ExtractResult (M.Map a b)
flipMExtractResult res = mapExtractResult M.fromList (flipExtractResult (map (\(key, (list, vars, res)) -> (list, vars, (key, res))) (M.toList res)))



pattAsVarSet :: AbstractPatt -> S.Set AbstractVar
pattAsVarSet patt = case patt of
    AbstractPattString _ -> S.empty
    AbstractPattInt _ -> S.empty
    AbstractPattVar var -> S.singleton var
    AbstractPattStruct (AbstractStruct _ args) -> case args of
        AbstractArgsPrimitive _ -> throw (IllegalPrimitivePattern patt)
        AbstractArgsComposite args -> foldl' S.union S.empty (map pattAsVarSet (map (\(_, iexpr) -> instExprAsPatt iexpr) args))

findFreeVarsAbstractArgs :: AbstractArgs -> S.Set AbstractVar
findFreeVarsAbstractArgs args = case args of
    AbstractArgsPrimitive iexpr -> findFreeVarsAbstractInstExpr iexpr
    AbstractArgsComposite args -> foldl' S.union S.empty (map (\(_, iexpr) -> findFreeVarsAbstractInstExpr iexpr) args)

findFreeVarsAbstractBoolExpr :: AbstractBoolExpr -> S.Set AbstractVar
findFreeVarsAbstractBoolExpr bexpr = case bexpr of
    AbstractBoolExprTrue -> S.empty
    AbstractBoolExprNeg bexpr -> findFreeVarsAbstractBoolExpr bexpr
    AbstractBoolExprCheck _ iexpr -> findFreeVarsAbstractInstExpr iexpr
    AbstractBoolExprBoolBinOp _ lhs rhs -> S.union (findFreeVarsAbstractBoolExpr lhs) (findFreeVarsAbstractBoolExpr rhs)
    AbstractBoolExprInstBinOp _ lhs rhs -> S.union (findFreeVarsAbstractInstExpr lhs) (findFreeVarsAbstractInstExpr rhs)

findFreeVarsAbstractInstExpr :: AbstractInstExpr -> S.Set AbstractVar
findFreeVarsAbstractInstExpr iexpr = case iexpr of
    AbstractInstExprString _ -> S.empty
    AbstractInstExprInt _ -> S.empty
    AbstractInstExprVar var -> S.singleton var
    AbstractInstExprProj iexpr _ -> findFreeVarsAbstractInstExpr iexpr
    AbstractInstExprStruct (AbstractStruct _ args) -> findFreeVarsAbstractArgs args
    AbstractInstExprBinOp _ lhs rhs -> S.union (findFreeVarsAbstractInstExpr lhs) (findFreeVarsAbstractInstExpr rhs)
    AbstractInstExprAggr aggr list -> throw (UnextractAggregator aggr list)

findFreeVarsAbstractInstList :: AbstractInstList -> S.Set AbstractVar
findFreeVarsAbstractInstList list = case list of
    AbstractInstListFor _ vars list -> S.difference (findFreeVarsAbstractInstList list) (pattAsVarSet vars)
    AbstractInstListLet patt iexpr list -> S.difference (S.union (findFreeVarsAbstractInstExpr iexpr) (findFreeVarsAbstractInstList list)) (pattAsVarSet patt)
    AbstractInstListWhere list bexpr -> S.union (findFreeVarsAbstractInstList list) (findFreeVarsAbstractBoolExpr bexpr)
    AbstractInstListExpr iexpr -> findFreeVarsAbstractInstExpr iexpr
    AbstractInstListTuple iexprs -> foldl' S.union S.empty (map findFreeVarsAbstractInstExpr iexprs)

findFreeVars :: AbstractInstList -> [AbstractVar]
findFreeVars list = S.toList (findFreeVarsAbstractInstList list)



extrAbstractArgs :: AbstractSpec -> AbstractClause -> Safety -> [String] -> AbstractArgs -> ExtractResult AbstractArgs
extrAbstractArgs spec clause in_safe_position aggr_ids args = case args of
    AbstractArgsPrimitive iexpr -> mapExtractResult AbstractArgsPrimitive (extrAbstractInstExpr spec clause in_safe_position aggr_ids iexpr)
    AbstractArgsComposite args -> mapExtractResult AbstractArgsComposite (flipExtractResult (map ((\(field, (list, vars, res)) -> (list, vars, (field, res))) . (\(field, iexpr) -> (field, extrAbstractInstExpr spec clause (makeReplace in_safe_position) aggr_ids iexpr))) args))

extrAbstractBoolExpr :: AbstractSpec -> AbstractClause -> Safety -> [String] -> AbstractBoolExpr -> ExtractResult AbstractBoolExpr
extrAbstractBoolExpr spec clause in_safe_position aggr_ids bexpr = case bexpr of
    AbstractBoolExprTrue -> ([], [], bexpr)
    AbstractBoolExprNeg bexpr -> mapExtractResult AbstractBoolExprNeg (extrAbstractBoolExpr spec clause (makeSafe in_safe_position) aggr_ids bexpr)
    AbstractBoolExprCheck attr iexpr -> mapExtractResult (AbstractBoolExprCheck attr) (extrAbstractInstExpr spec clause (makeReplace in_safe_position) aggr_ids iexpr)
    AbstractBoolExprBoolBinOp op lhs rhs -> joinExtractResult (AbstractBoolExprBoolBinOp op) (extrAbstractBoolExpr spec clause (makeSafe in_safe_position) aggr_ids lhs) (extrAbstractBoolExpr spec clause (makeSafe in_safe_position) aggr_ids rhs)
    AbstractBoolExprInstBinOp op lhs rhs -> joinExtractResult (AbstractBoolExprInstBinOp op) (extrAbstractInstExpr spec clause (makeSafe in_safe_position) aggr_ids lhs) (extrAbstractInstExpr spec clause (makeSafe in_safe_position) aggr_ids rhs)

extrAbstractInstExpr :: AbstractSpec -> AbstractClause -> Safety -> [String] -> AbstractInstExpr -> ExtractResult AbstractInstExpr
extrAbstractInstExpr spec clause in_safe_position aggr_ids iexpr = case iexpr of
    AbstractInstExprAggr aggr list -> if in_safe_position == Safe
        then
            -- We can keep this aggregator, but we must nest
            mapExtractResult (AbstractInstExprAggr aggr) (extrAbstractInstList spec clause (makeNested in_safe_position) aggr_ids list)
        else
            -- Extract the aggregator
            (\(list, vars, res) ->
                -- We do one anonymous function deeper to generate unique but consistent variable names
                (\(list, vars, res) freevars varid instid -> (
                    -- We mark that a new type should be generated
                    list ++ [(varid, instid, freevars, (aggr, res))],
                    -- And that a new variable must be quantified over
                    vars ++ [AbstractPattStruct (AbstractStruct instid (AbstractArgsComposite ([(AbstractField varid AbstractTypeInt, AbstractInstExprVar (AbstractVar varid AbstractTypeInt))] ++ (map (\var -> (varAsField var, AbstractInstExprVar var)) freevars))))],
                    -- And finally, generate the variable that goes in-place of the aggregator
                    AbstractInstExprVar (AbstractVar varid AbstractTypeInt)
                    -- AbstractInstExprStruct (AbstractStruct instid ([(AbstractField varid AbstractTypeInt, AbstractInstExprVar (AbstractVar varid AbstractTypeInt))] ++ (map (\var -> (varAsField var, AbstractInstExprVar var)) freevars)))
                )) (list, vars, res) (findFreeVars res) (genUniqueIdInContext clause (map (\(varid, _, _, _) -> varid) list)) (genUniqueInstIdInContext spec aggr_ids "aggr_a")
            ) (extrAbstractInstList spec clause (makeNested in_safe_position) aggr_ids list)

    -- Trivial cases
    AbstractInstExprString _ -> ([], [], iexpr)
    AbstractInstExprInt _ -> ([], [], iexpr)
    AbstractInstExprVar _ -> ([], [], iexpr)
    AbstractInstExprProj iexpr field -> mapExtractResult ((flip AbstractInstExprProj) field) (extrAbstractInstExpr spec clause (makeReplace in_safe_position) aggr_ids iexpr)
    AbstractInstExprStruct (AbstractStruct ty args) -> mapExtractResult (\args -> AbstractInstExprStruct (AbstractStruct ty args)) (extrAbstractArgs spec clause (makeReplace in_safe_position) aggr_ids args)
    AbstractInstExprBinOp op lhs rhs -> joinExtractResult (AbstractInstExprBinOp op) (extrAbstractInstExpr spec clause (makeReplace in_safe_position) aggr_ids lhs) (extrAbstractInstExpr spec clause (makeReplace in_safe_position) aggr_ids rhs)

extrAbstractInstList :: AbstractSpec -> AbstractClause -> Safety -> [String] -> AbstractInstList -> ExtractResult AbstractInstList
extrAbstractInstList spec clause in_safe_position aggr_ids list = generateFor (case list of
                                                                      AbstractInstListFor attr vars list -> mapExtractResult (AbstractInstListFor attr vars) (extrAbstractInstList spec clause (makeReplace in_safe_position) aggr_ids list)
                                                                      AbstractInstListLet patt iexpr list -> joinExtractResult (AbstractInstListLet patt) (extrAbstractInstExpr spec clause (makeSafe in_safe_position) aggr_ids iexpr) (extrAbstractInstList spec clause (makeReplace in_safe_position) aggr_ids list)
                                                                      AbstractInstListWhere list bexpr -> joinExtractResult AbstractInstListWhere (extrAbstractInstList spec clause (makeReplace in_safe_position) aggr_ids list) (extrAbstractBoolExpr spec clause (makeSafe in_safe_position) aggr_ids bexpr)
                                                                      AbstractInstListExpr iexpr -> mapExtractResult AbstractInstListExpr (extrAbstractInstExpr spec clause (makeReplace in_safe_position) aggr_ids iexpr)
                                                                      AbstractInstListTuple iexprs -> mapExtractResult AbstractInstListTuple (flipExtractResult (map (extrAbstractInstExpr spec clause (makeReplace in_safe_position) aggr_ids) iexprs)))
                                                                  where generateFor (list, [], res) = (list, [], res)
                                                                        generateFor (list, (head:rem), res) = generateFor (list, rem, AbstractInstListFor AbstractInputAttrEnum (head) res)

extrAbstractClause :: AbstractSpec -> [String] -> AbstractClause -> ExtractResult AbstractClause
extrAbstractClause spec aggr_ids clause = case clause of
    AbstractClauseDerive list -> mapExtractResult AbstractClauseDerive (extrAbstractInstList spec clause Replace aggr_ids list)
    AbstractClauseEffect list attr -> mapExtractResult ((flip AbstractClauseEffect) attr) (extrAbstractInstList spec clause Replace aggr_ids list)
    AbstractClauseFilter bexpr attr -> mapExtractResult ((flip AbstractClauseFilter) attr) (extrAbstractBoolExpr spec clause Safe aggr_ids bexpr)
    AbstractClauseInfinite -> ([], [], AbstractClauseInfinite)
    AbstractClauseFinite insts -> mapExtractResult AbstractClauseFinite (flipExtractResult (map (\(list, vars, res) -> (list, vars, instExprAsInst res)) (map ((extrAbstractInstExpr spec clause Replace aggr_ids) . instAsInstExpr) insts)))
    AbstractClauseAct -> ([], [], AbstractClauseAct)

extrAbstractTypeSpec :: AbstractSpec -> [String] -> AbstractTypeSpec -> ExtractResult AbstractTypeSpec
extrAbstractTypeSpec spec aggr_ids (AbstractTypeSpec fields clauses) = mapExtractResult (AbstractTypeSpec fields) (mapExtractResult S.fromList (flipExtractResult (map (extrAbstractClause spec aggr_ids) (S.toList clauses))))

varsAsFors :: AbstractInputAttr -> [AbstractVar] -> AbstractInstList -> AbstractInstList
varsAsFors _ [] list = list
varsAsFors attr (head:rem) list = AbstractInstListFor attr (AbstractPattVar head) (varsAsFors attr rem list)
processExtractResult :: ExtractResult (M.Map String AbstractTypeSpec) -> (M.Map String AbstractTypeSpec)
processExtractResult (list, [], res) = M.union res (M.fromList (map (\(_, instid, freevars, (aggr, list)) ->
        (\instid freevars aggr list intfieldid ->
            (
                instid,
                AbstractTypeSpec
                    -- The type's fields are the aggregator value + free variables
                    (AbstractFieldsComposite ([AbstractField intfieldid (AbstractTypeInt)] ++ (map varAsField freevars)))
                    (S.fromList [
                        -- There is a clause to enum this type
                        AbstractClauseInfinite,
                        -- There's a clause that derives every element
                        -- This is a quantification over all free variables to build the struct...
                        AbstractClauseDerive (varsAsFors AbstractInputAttrEnum freevars (
                            -- ...with a binding for the aggregator value...
                            AbstractInstListLet (AbstractPattVar (AbstractVar intfieldid AbstractTypeInt)) (AbstractInstExprAggr aggr list) (
                                -- ...and then a struct that uses the binding + the quantification to build the type
                                AbstractInstListExpr (AbstractInstExprStruct (AbstractStruct instid (AbstractArgsComposite ([(AbstractField intfieldid AbstractTypeInt, AbstractInstExprVar (AbstractVar intfieldid AbstractTypeInt))] ++ (map (\var -> (varAsField var, AbstractInstExprVar var)) freevars)))))
                            )
                        ))
                    ])
            )
        ) instid freevars aggr list (genUniqueIdInContext AbstractClauseInfinite (map (\(AbstractVar id _) -> id) freevars))
    ) list))
processExtractResult (_, vars, _) = throw (UnprocessedVars vars)
extrAbstractSpec :: AbstractSpec -> AbstractSpec
extrAbstractSpec spec@(AbstractSpec tys) = AbstractSpec (processExtractResult (flipMExtractResult (M.foldlWithKey' (\res name tyspec -> M.union res (M.singleton name (extrAbstractTypeSpec spec (foldl' (++) [] (map (\(list, _, _) -> (map (\(_, instvar, _, _) -> instvar) list)) (M.elems res))) tyspec))) M.empty tys)))





-- ----- UNSPECIFIED FIELD DESUGARING -----
-- -- Exceptions throw in the `specfield` traversal
-- data SpecifyFieldException = LeftoverFreeVars [AbstractVar]
--                            | SFUndeclaredType String
--                            | Unreachable
--                            deriving(Show, Typeable)
-- instance Exception SpecifyFieldException



-- -- Keeps track of variables that we yet have to bind
-- type WithFreeVars a = ([AbstractVar], a)

-- noFreeVars :: a -> WithFreeVars a
-- noFreeVars obj = ([], obj)

-- mapWithFreeVars :: (a -> b) -> WithFreeVars a -> WithFreeVars b
-- mapWithFreeVars pred (context, obj) = (context, pred obj)

-- joinWithFreeVars :: (a -> b -> c) -> WithFreeVars a -> WithFreeVars b -> WithFreeVars c
-- joinWithFreeVars pred (lcontext, lobj) (rcontext, robj) = (lcontext ++ rcontext, pred lobj robj)

-- flipWithFreeVars :: [WithFreeVars a] -> WithFreeVars [a]
-- flipWithFreeVars [] = ([], [])
-- flipWithFreeVars ((context, obj):rem) = (context ++ (fst (flipWithFreeVars rem)), [obj] ++ (snd (flipWithFreeVars rem)))

-- bindFreeVars :: AbstractPatt -> WithFreeVars a -> WithFreeVars a
-- bindFreeVars patt (vars, obj) = case patt of
--     AbstractPattString _ -> (vars, obj)
--     AbstractPattInt _ -> (vars, obj)
--     AbstractPattVar var -> (filter (not . ((==) var)) vars, obj)
--     AbstractPattStruct (AbstractStruct _ args) -> case args of
--         AbstractArgsPrimitive iexpr -> bindFreeVars (instExprAsPatt iexpr) (vars, obj)
--         AbstractArgsComposite args -> foldl' (\(vars, obj) (_, iexpr) -> bindFreeVars (instExprAsPatt iexpr) (vars, obj)) (vars, obj) args

-- processFreeVars :: WithFreeVars AbstractInstList -> AbstractInstList
-- processFreeVars ([], list) = list
-- processFreeVars ((var:rem), list) = AbstractInstListFor AbstractInputAttrEnum (AbstractPattVar var) (processFreeVars (rem, list))

-- assertNoFreeVars :: WithFreeVars a -> a
-- assertNoFreeVars ([], obj) = obj
-- assertNoFreeVars (vars, _) = throw (LeftoverFreeVars vars)



-- specfieldAbstractBoolExpr :: AbstractSpec -> AbstractBoolExpr -> WithFreeVars AbstractBoolExpr
-- specfieldAbstractBoolExpr spec bexpr = case bexpr of
--     AbstractBoolExprTrue -> ([], bexpr)
--     AbstractBoolExprNeg bexpr -> mapWithFreeVars AbstractBoolExprNeg (specfieldAbstractBoolExpr spec bexpr)
--     AbstractBoolExprCheck attr iexpr -> mapWithFreeVars (AbstractBoolExprCheck attr) (specfieldAbstractInstExpr spec iexpr)
--     AbstractBoolExprBoolBinOp op lhs rhs -> joinWithFreeVars (AbstractBoolExprBoolBinOp op) (specfieldAbstractBoolExpr spec lhs) (specfieldAbstractBoolExpr spec rhs)
--     AbstractBoolExprInstBinOp op lhs rhs -> joinWithFreeVars (AbstractBoolExprInstBinOp op) (specfieldAbstractInstExpr spec lhs) (specfieldAbstractInstExpr spec rhs)

-- specfieldAbstractInstExpr :: AbstractSpec -> AbstractInstExpr -> WithFreeVars AbstractInstExpr
-- specfieldAbstractInstExpr spec@(AbstractSpec tys) iexpr = case iexpr of
--     -- The struct
--     AbstractInstExprStruct (AbstractStruct name args) -> case args of
--         AbstractArgsPrimitive iexpr -> mapWithFreeVars (AbstractInstExprStruct . (AbstractStruct name) . AbstractArgsPrimitive) (specfieldAbstractInstExpr spec iexpr)
--         AbstractArgsComposite args -> case (M.lookup name tys) of
--             Just (AbstractTypeSpec fields _) -> case fields of
--                 -- Composite types are the _really_ interesting ones. Now we set out to inject missing variables
--                 AbstractFieldsComposite fields ->
--                     injectMissingVars (flipWithFreeVars (map (specfieldAbstractInstExpr spec) (snd (unzip args))))
--                     where injectMissingVars :: WithFreeVars [AbstractInstExpr] -> WithFreeVars AbstractInstExpr
--                           injectMissingVars (context, iexprs) = (context ++ (filter (not . ((flip elem) (map fieldAsVar (fst (unzip args))))) (map fieldAsVar fields)), AbstractInstExprStruct (AbstractStruct name (AbstractArgsComposite (map (\field -> case (lookup field args) of { Just iexpr -> (field, iexpr); Nothing -> (field, AbstractInstExprVar (fieldAsVar field)) }) fields))))

--                 -- For the atomic types, we assume all are given
--                 AbstractFieldsAtomicClose _ -> ([], AbstractInstExprStruct (AbstractStruct name (AbstractArgsComposite args)))
--                 AbstractFieldsAtomicOpen _ -> ([], AbstractInstExprStruct (AbstractStruct name (AbstractArgsComposite args)))
--             Nothing -> throw (SFUndeclaredType name)

--     -- The usual traversing ones
--     AbstractInstExprString _ -> ([], iexpr)
--     AbstractInstExprInt _ -> ([], iexpr)
--     AbstractInstExprVar _ -> ([], iexpr)
--     AbstractInstExprProj iexpr field -> mapWithFreeVars ((flip AbstractInstExprProj) field) (specfieldAbstractInstExpr spec iexpr)
--     AbstractInstExprBinOp op lhs rhs -> joinWithFreeVars (AbstractInstExprBinOp op) (specfieldAbstractInstExpr spec lhs) (specfieldAbstractInstExpr spec rhs)
--     AbstractInstExprAggr aggr list -> mapWithFreeVars (AbstractInstExprAggr aggr) (specfieldAbstractInstList spec list)

-- specfieldAbstractInstList :: AbstractSpec -> AbstractInstList -> WithFreeVars AbstractInstList
-- specfieldAbstractInstList spec list = case list of
--     AbstractInstListFor attr patt list ->  bindFreeVars patt (mapWithFreeVars (AbstractInstListFor attr patt) (specfieldAbstractInstList spec list))
--     AbstractInstListLet patt iexpr list -> bindFreeVars patt (joinWithFreeVars (AbstractInstListLet patt) (specfieldAbstractInstExpr spec iexpr) (specfieldAbstractInstList spec list))
--     AbstractInstListWhere list bexpr -> joinWithFreeVars AbstractInstListWhere (specfieldAbstractInstList spec list) (specfieldAbstractBoolExpr spec bexpr)
--     AbstractInstListExpr iexpr -> mapWithFreeVars AbstractInstListExpr (specfieldAbstractInstExpr spec iexpr)
--     AbstractInstListTuple iexprs -> mapWithFreeVars AbstractInstListTuple (flipWithFreeVars (map (specfieldAbstractInstExpr spec) iexprs))

-- specfieldAbstractClause :: AbstractSpec -> AbstractClause -> AbstractClause
-- specfieldAbstractClause spec clause = case clause of
--     AbstractClauseDerive list -> AbstractClauseDerive (processFreeVars (specfieldAbstractInstList spec list))
--     AbstractClauseEffect list effect -> AbstractClauseEffect (processFreeVars (specfieldAbstractInstList spec list)) effect
--     AbstractClauseFilter bexpr filter -> AbstractClauseFilter (assertNoFreeVars (specfieldAbstractBoolExpr spec bexpr)) filter
--     AbstractClauseFinite insts -> AbstractClauseFinite insts
--     AbstractClauseInfinite -> AbstractClauseInfinite
--     AbstractClauseAct -> AbstractClauseAct

-- specfieldAbstractTypeSpec :: AbstractSpec -> AbstractTypeSpec -> AbstractTypeSpec
-- specfieldAbstractTypeSpec spec (AbstractTypeSpec fields clauses) = AbstractTypeSpec fields (S.map (specfieldAbstractClause spec) clauses)

-- -- Given a spec, will inject variables for all missing fields.
-- specfieldAbstractSpec :: AbstractSpec -> AbstractSpec
-- specfieldAbstractSpec spec@(AbstractSpec tys) = AbstractSpec (M.map (specfieldAbstractTypeSpec spec) tys)

-- specfieldAbstractScenario :: AbstractSpec -> AbstractScenario -> AbstractScenario
-- specfieldAbstractScenario spec (AbstractScenario lists) = AbstractScenario (zip ((map (processFreeVars . (specfieldAbstractInstList spec)) (fst (unzip lists)))) (snd (unzip lists)))





----- TRAVERSALS: RESOLVE FREE VARIABLES IN SCENARIOS -----
-- Exceptions throw in the `specfield` traversal
data SpecifyFieldException = LeftoverFreeVars [AbstractVar]
                           | SFUndeclaredType String
                           | Unreachable
                           deriving(Show, Typeable)
instance Exception SpecifyFieldException



-- Keeps track of variables that we yet have to bind
type WithFreeVars a = ([AbstractVar], a)

noFreeVars :: a -> WithFreeVars a
noFreeVars obj = ([], obj)

mapWithFreeVars :: (a -> b) -> WithFreeVars a -> WithFreeVars b
mapWithFreeVars pred (context, obj) = (context, pred obj)

joinWithFreeVars :: (a -> b -> c) -> WithFreeVars a -> WithFreeVars b -> WithFreeVars c
joinWithFreeVars pred (lcontext, lobj) (rcontext, robj) = (lcontext ++ rcontext, pred lobj robj)

flipWithFreeVars :: [WithFreeVars a] -> WithFreeVars [a]
flipWithFreeVars [] = ([], [])
flipWithFreeVars ((context, obj):rem) = (context ++ (fst (flipWithFreeVars rem)), [obj] ++ (snd (flipWithFreeVars rem)))

bindFreeVars :: AbstractPatt -> WithFreeVars a -> WithFreeVars a
bindFreeVars patt (vars, obj) = case patt of
    AbstractPattString _ -> (vars, obj)
    AbstractPattInt _ -> (vars, obj)
    AbstractPattVar var -> (filter (not . ((==) var)) vars, obj)
    AbstractPattStruct (AbstractStruct _ args) -> case args of
        AbstractArgsPrimitive iexpr -> bindFreeVars (instExprAsPatt iexpr) (vars, obj)
        AbstractArgsComposite args -> foldl' (\(vars, obj) (_, iexpr) -> bindFreeVars (instExprAsPatt iexpr) (vars, obj)) (vars, obj) args

processFreeVars :: WithFreeVars AbstractInstList -> AbstractInstList
processFreeVars ([], list) = list
processFreeVars ((var:rem), list) = AbstractInstListFor AbstractInputAttrEnum (AbstractPattVar var) (processFreeVars (rem, list))

assertNoFreeVars :: WithFreeVars a -> a
assertNoFreeVars ([], obj) = obj
assertNoFreeVars (vars, _) = throw (LeftoverFreeVars vars)



fixfreeAbstractBoolExpr :: AbstractBoolExpr -> WithFreeVars AbstractBoolExpr
fixfreeAbstractBoolExpr bexpr = case bexpr of
    AbstractBoolExprTrue -> noFreeVars bexpr
    AbstractBoolExprNeg bexpr -> mapWithFreeVars AbstractBoolExprNeg (fixfreeAbstractBoolExpr bexpr)
    AbstractBoolExprCheck attr iexpr -> mapWithFreeVars (AbstractBoolExprCheck attr) (fixfreeAbstractInstExpr iexpr)
    AbstractBoolExprBoolBinOp op lhs rhs -> joinWithFreeVars (AbstractBoolExprBoolBinOp op) (fixfreeAbstractBoolExpr lhs) (fixfreeAbstractBoolExpr rhs)
    AbstractBoolExprInstBinOp op lhs rhs -> joinWithFreeVars (AbstractBoolExprInstBinOp op) (fixfreeAbstractInstExpr lhs) (fixfreeAbstractInstExpr rhs)

fixfreeAbstractInstExpr :: AbstractInstExpr -> WithFreeVars AbstractInstExpr
fixfreeAbstractInstExpr iexpr = case iexpr of
    AbstractInstExprString _ -> noFreeVars iexpr
    AbstractInstExprInt _ -> noFreeVars iexpr
    AbstractInstExprVar var -> ([var], AbstractInstExprVar var)
    AbstractInstExprProj iexpr field -> mapWithFreeVars ((flip AbstractInstExprProj) field) (fixfreeAbstractInstExpr iexpr)
    AbstractInstExprStruct (AbstractStruct name args) -> case args of
        AbstractArgsPrimitive iexpr -> mapWithFreeVars (AbstractInstExprStruct . (AbstractStruct name) . AbstractArgsPrimitive) (fixfreeAbstractInstExpr iexpr)
        AbstractArgsComposite args -> mapWithFreeVars (AbstractInstExprStruct . (AbstractStruct name) . AbstractArgsComposite) (flipWithFreeVars (map (\(field, iexpr) -> (\(vars, iexpr) -> (vars, (field, iexpr))) (fixfreeAbstractInstExpr iexpr)) args))
    AbstractInstExprBinOp op lhs rhs -> joinWithFreeVars (AbstractInstExprBinOp op) (fixfreeAbstractInstExpr lhs) (fixfreeAbstractInstExpr rhs)
    AbstractInstExprAggr aggr list -> mapWithFreeVars (AbstractInstExprAggr aggr) (fixfreeAbstractInstList list)

fixfreeAbstractInstList :: AbstractInstList -> WithFreeVars AbstractInstList
fixfreeAbstractInstList list = case list of
    AbstractInstListFor attr patt list -> mapWithFreeVars (AbstractInstListFor attr patt) (bindFreeVars patt (fixfreeAbstractInstList list))
    AbstractInstListLet patt iexpr list -> joinWithFreeVars (AbstractInstListLet patt) (fixfreeAbstractInstExpr iexpr) (bindFreeVars patt (fixfreeAbstractInstList list))
    AbstractInstListWhere list bexpr -> joinWithFreeVars AbstractInstListWhere (fixfreeAbstractInstList list) (fixfreeAbstractBoolExpr bexpr)
    AbstractInstListExpr iexpr -> mapWithFreeVars AbstractInstListExpr (fixfreeAbstractInstExpr iexpr)
    AbstractInstListTuple iexprs -> mapWithFreeVars AbstractInstListTuple (flipWithFreeVars (map fixfreeAbstractInstExpr iexprs))

fixfreeAbstractGroup :: AbstractGroup -> AbstractGroup
fixfreeAbstractGroup (AbstractGroup effects) = AbstractGroup (map (\(list, effect) -> (processFreeVars (fixfreeAbstractInstList list), effect)) effects)

-- Finds free variables in scenarios and injects foreaches where missing.
fixfreeAbstractScenario :: AbstractScenario -> AbstractScenario
fixfreeAbstractScenario (AbstractScenario groups) = AbstractScenario (map fixfreeAbstractGroup groups)





----- STAGE 1: Normalization -----
-- 1. Boolean expressions must be in conjunctive normal form (V)
-- 2. <see paper>
-- 3. No projection (V)
-- 4. No nested aggregators, no disjunction in aggregators
-- 5. Aggregators are only used for filtering (V)
-- 6. Ensure that all clauses translate to one clause (I think this is guaranteed when doing the above)
normalizeAbstractSpec :: AbstractSpec -> AbstractSpec
-- normalizeAbstractSpec spec = deprojAbstractSpec (extrAbstractSpec (specfieldAbstractSpec (cnfAbstractSpec spec)))
normalizeAbstractSpec spec = deprojAbstractSpec (extrAbstractSpec (cnfAbstractSpec spec))

-- Translates scenarios into fragments of Clingo
normalizeAbstractScenario :: AbstractSpec -> AbstractScenario -> AbstractScenario
-- normalizeAbstractScenario spec scenario = deprojAbstractScenario spec (specfieldAbstractScenario spec (cnfAbstractScenario scenario))
normalizeAbstractScenario spec scenario = deprojAbstractScenario spec (fixfreeAbstractScenario (cnfAbstractScenario scenario))
