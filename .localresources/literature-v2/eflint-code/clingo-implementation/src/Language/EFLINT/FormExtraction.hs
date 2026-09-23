{-# LANGUAGE TupleSections #-}

module Language.EFLINT.FormExtraction where

import Language.EFLINT.Spec
import Language.EFLINT.State
import Language.EFLINT.Eval

import Data.List ((\\))
import qualified Data.Map as M 
import qualified Data.Set as S

form_all_open :: Spec -> State -> S.Set MissingInput 
form_all_open spec = form_from_set (M.keysSet (decls spec)) spec

form_from_phrases :: [Phrase] -> Spec -> State -> S.Set MissingInput
form_from_phrases ps spec state = form_from_set reachables spec state
  where reachables = S.unions (map (reachable spec) ps)

reachable :: Spec -> Phrase -> S.Set DomId
reachable spec p = M.keysSet (decls spec) 
{-
 PDo Tagged
            | PTrigger [Var] Term
            | Create [Var] Term
            | Terminate [Var] Term
            | Obfuscate [Var] Term
            | PQuery Term
            | PInstQuery [Var] Term
            | PDeclBlock [Decl]
            | PSkip
 -}

reachable_term :: Spec -> Term -> S.Set DomId
reachable_term spec term = S.empty

reachable_foreach :: Spec -> [Var] -> Term -> S.Set DomId 
reachable_foreach spec vars t = 
  S.fromList (map (remove_decoration spec) vars) `S.union` reachable_term spec t                                

form_from_set :: S.Set DomId -> Spec -> State -> S.Set MissingInput
form_from_set set spec state = 
  S.map (mk_missing spec state) $ S.filter isOpen set 
  where isOpen d = case closed_type spec d of Just False -> True
                                              _          -> False

mk_missing :: Spec -> State -> DomId {- open -} -> MissingInput
mk_missing spec state d = 
 case runSubs (every_valid_subs (no_decoration d)) spec state M.empty of
  Left (MissingInput mi)  -> mi -- either MissingAssignments or MissingInstances
  Left err                -> error $ "assert 2 mk_missing" ++ print_runtime_error err 
  Right tes               -> missing_assignments trues falses ((tes \\ trues) \\ falses) (restriction_of spec d)
    where (trues, falses) = assigned_instances state d

