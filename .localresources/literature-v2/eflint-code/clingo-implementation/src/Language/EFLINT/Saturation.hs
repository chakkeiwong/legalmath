{-# LANGUAGE LambdaCase #-}

module Language.EFLINT.Saturation (rebase_and_sat) where

import Language.EFLINT.Spec
import Language.EFLINT.State
import Language.EFLINT.Eval

import Control.Monad (foldM)

import qualified Data.Map as M
import qualified Data.Set as S

-- the monad has been introduced here to propagate missing input exceptions
-- a mechanism is needed to provide input in parallel with declarations
-- to accommodate the situation where a derivation rule is used that interacts with an open type
rebase_and_sat :: Spec -> State -> M_Subs State
rebase_and_sat spec = saturate spec . rebase spec

rebase :: Spec -> State -> State
rebase spec s = s { contents = M.filterWithKey op (contents s) }
  where op (_,d) i = not (from_sat i)

saturate :: Spec -> State -> M_Subs State
saturate spec state = saturate' spec state >>= \case 
  state' | state == state' -> return state
         | otherwise       -> saturate spec state'
 where 
  saturate' spec s = foldM op s (S.toList (derived spec))
    where op s d = case find_decl spec d of 
                    Nothing -> return s
                    Just tdecl -> foldM clause s (derivation tdecl) 
                      where clause s (HoldsWhen t) 
                             | Products xs <- domain tdecl = derive xs (When (App d $ Right []) t) s
                             | otherwise = derive [no_decoration d] (When (Ref $ no_decoration d) t) s
                            clause s (Dv xs t) = derive xs t s
            where derive xs t s = let dyn = foreach xs $
                                              checkFilter sat_conditions (whenTagged (eval t) return)
                                  in case runSubs dyn spec s M.empty of
                                        Left error -> err error
                                        Right ress -> return $ derive_all (concat ress) s

