{-# LANGUAGE TupleSections #-}

module Language.EFLINT.State where

import Language.EFLINT.Spec

import Data.Maybe (isJust)
import qualified Data.Map as M

import Control.Applicative (empty)

data Info   = Info {
                value :: Bool
              , from_sat :: Bool -- whether assignment came from saturation process
              }
              deriving (Eq, Read, Show)

data State =  State {
                  contents :: M.Map Tagged Info  -- meta-info about components
              ,   time :: Int
              }
              deriving Eq

data Transition = Transition {
                    tagged :: Tagged
                  , exist :: Bool
                  }  
                  deriving (Ord, Eq, Show, Read)

type Store = M.Map Tagged Assignment 

data Assignment = HoldsTrue
                | HoldsFalse
                | Unknown
                deriving (Eq, Ord, Show, Read)

toAssignment :: Maybe Bool -> Assignment
toAssignment (Just True) = HoldsTrue
toAssignment (Just False) = HoldsFalse
toAssignment Nothing = Unknown

emptyStore = M.empty

-- | biased union over stores, precedence HoldsTrue > HoldsFalse > Unknown
store_union :: Store -> Store -> Store
store_union = M.unionWith op
  where op HoldsTrue _      = HoldsTrue
        op _ HoldsTrue      = HoldsTrue
        op HoldsFalse _     = HoldsFalse
        op _ HoldsFalse     = HoldsFalse
        op Unknown Unknown  = Unknown
store_unions :: [Store] -> Store
store_unions = foldr store_union emptyStore

missing_assignments :: [Tagged] -> [Tagged] -> [Tagged] -> Maybe Restriction -> MissingInput
missing_assignments trues falses unknowns mres = MissingAssignments (M.unions
  [M.fromList $ map (,HoldsTrue) trues 
  ,M.fromList $ map (,HoldsFalse) falses 
  ,M.fromList $ map (,Unknown) unknowns]) mres

make_assignments :: Spec -> Store -> State -> State
make_assignments spec = flip (M.foldrWithKey op)
  where op te@(_,d) HoldsTrue = case restriction_of spec d of
              Just VarRestriction      -> var_assignment te
              Just FunctionRestriction -> function_assignment te
              _                        -> create te
        op te HoldsFalse  = terminate te
        op te Unknown     = obfuscate te

        create :: Tagged -> State -> State
        create te s = s { contents = M.insert te Info{ value = True, from_sat = False } (contents s) }

        terminate :: Tagged -> State -> State
        terminate te s = s { contents = M.insert te Info{ value = False, from_sat = False } (contents s) }

        obfuscate :: Tagged -> State -> State
        obfuscate te s = s { contents = M.delete te (contents s) }

        var_assignment :: Tagged -> State -> State
        var_assignment te@(_,d) s = create te $ s { contents = M.mapWithKey op (contents s) }
          where op te@(_,d') i | d == d'   = i { value = False, from_sat = False }
                               | otherwise = i

        function_assignment :: Tagged -> State -> State
        function_assignment te@(Product [f,t], d) s = 
          create te $ s { contents = M.mapWithKey op (contents s) }
          where op (Product [f',t'], d') i | d == d' && f == f' = i { value = False, from_sat = False }
                op _ i = i
        function_assignment _ s = s


derive :: Tagged -> State -> State
derive te s = s { contents = M.alter adj te (contents s) }
  where adj Nothing     = Just $ Info{ value = True, from_sat = True }
        adj (Just info) = Just info

derive_all :: [Tagged] -> State -> State
derive_all = flip (foldr derive)

-- | assumes the instance of a closed type
holds :: Tagged -> State -> Bool
holds te s = maybe False ((==True) . value) (M.lookup te (contents s))

emptyState = State { contents = M.empty, time = 0 }

increment_time state = state { time = 1 + (time state) }

instance Show State where
  show state = unlines $ 
      [ show_component c ++ " = " ++ show (value m)
      | (c,m) <- M.assocs (contents state)
      ]

-- instance ToJSON State where
-- toJSON state = toJSON (map TaggedJSON (state_holds state)) 

state_holds :: State -> [Tagged]
state_holds state = [ te | (te, m) <- M.assocs (contents state), True == value m ]

state_not_holds :: State -> [Tagged]
state_not_holds state = [ te | (te, m) <- M.assocs (contents state), False == value m ]

assigned_instances :: State -> DomId -> ([Tagged], [Tagged])
assigned_instances state d = 
  ([ te | (te@(_,d'), m) <- M.assocs (contents state), d == d', value m == True ] 
  ,[ te | (te@(_,d'), m) <- M.assocs (contents state), d == d', value m == False ] 
  )

data Context = Context {
                  ctx_spec        :: Spec --mutable, fixed?
                , ctx_state       :: State --mutable 
                , ctx_transitions :: [Transition] -- (label * enabled?) -- replaceable
                , ctx_duties      :: [Tagged] -- replaceable
                }

-- mutable means c0 ; c1 results in c1 adding to c0 with possible override
-- appendable means c0 ; c1 results in effects of c0 and c1 being concatenated
-- replaceable means c0 ; c1 results in effect of c1

emptyContext spec = 
               Context { 
                  ctx_spec = spec
                , ctx_state = emptyState
                , ctx_transitions = empty
                , ctx_duties = empty }

data TransInfo = TransInfo {
                  trans_tagged      :: Tagged 
                , trans_assignments :: Store  -- includes sync'ed effects
                , trans_forced      :: Bool -- whether this or a sync'ed transition is not enabled was forced (i.e. was not enabled)
                , trans_actor       :: Maybe Tagged
                , trans_syncs       :: [TransInfo] -- the transitions this transitions sync'ed with 
                }
                deriving (Eq, Ord, Show, Read) 

trans_is_action :: TransInfo -> Bool
trans_is_action = isJust . trans_actor

-- | Get all the TransInfo nodes in the tree represented by the given root
trans_all_infos :: TransInfo -> [TransInfo]
trans_all_infos info = info : concatMap trans_all_infos (trans_syncs info)

data Violation = DutyViolation      Tagged
               | TriggerViolation   TransInfo 
               | InvariantViolation DomId
               deriving (Ord, Eq, Show, Read) 

data QueryRes = QuerySuccess
              | QueryFailure
              deriving (Ord, Eq, Show, Read)

data Error = -- trigger errors
             NotTriggerable DomId 
           | CompilationError String
           | RuntimeError RuntimeError
           deriving (Eq, Ord, Show, Read) 

data RuntimeError
      = MissingInput MissingInput 
      | InternalError InternalError
      deriving (Eq, Ord, Show, Read) 

data MissingInput 
      = MissingAssignments  Store (Maybe Restriction)  -- all Tagged have same DomId component, complete wrt finite dom
      | MissingInstances    DomId MDomain (Maybe Restriction)
      deriving (Eq, Ord, Show, Read) 

data MDomain    = MAnyString
                | MAnyInt
                | MStrings [String]
                | MInts [Int]
                | MProducts [(DomId, MDomain)]
                deriving (Ord, Eq, Show, Read)

data InternalError 
      = EnumerateInfiniteDomain DomId Domain 
      | MissingSubstitution Var
      | PrimitiveApplication DomId
      | UndeclaredType DomId 
      deriving (Eq, Ord, Show, Read)

print_error :: Error -> String
print_error (NotTriggerable d) = "not a triggerable (act- or event-) type: " ++ d
print_error (CompilationError err) = err
print_error (RuntimeError err) = print_runtime_error err

print_runtime_error :: RuntimeError -> String
print_runtime_error (MissingInput miss) = case miss of
  MissingAssignments tes _ -> "missing input assignments for: " ++ show (map ppTagged (M.keys tes))
  MissingInstances domid dom _ -> "missing input assignments for type: " ++ domid
print_runtime_error (InternalError err) = "INTERNAL ERROR " ++ print_internal_error err

print_internal_error :: InternalError -> String
print_internal_error (EnumerateInfiniteDomain d AnyString) = "cannot enumerate all strings of type: " ++ d
print_internal_error (EnumerateInfiniteDomain d AnyInt) = "cannot enumerate all integers of type: " ++ d
print_internal_error (EnumerateInfiniteDomain d _) = "cannot enumerate all instances of type: " ++ d
print_internal_error (MissingSubstitution (Var base dec)) = "variable " ++ base ++ dec ++ " not bound"
print_internal_error (PrimitiveApplication d) = "application of primitive type: " ++ d
print_internal_error (UndeclaredType d) = "undeclared type: " ++ d
