{-# LANGUAGE OverloadedStrings #-}

module Language.EFLINT.Spec where

import Data.Foldable (asum)
import Data.List (intercalate)
import qualified Data.Map as M
import qualified Data.Set as S

import Control.Monad (join)

import Data.Aeson hiding (String)
import qualified Data.Aeson as JSON

type DomId      = String -- type identifiers
type Tagged     = (Elem, DomId)

data Var        = Var DomId String {- decoration -}
                deriving (Ord, Eq, Show, Read)

data Elem       = String String 
                | Int Int
                | Product [Tagged]
                deriving (Ord, Eq, Show, Read)

data Domain     = AnyString
                | AnyInt
                | Strings [String]
                | Ints [Int]
                | Products [Var]
                | Time
                deriving (Ord, Eq, Show, Read)

enumerable :: Spec -> Domain -> Bool
enumerable spec d = case d of
  Strings _     -> True
  Ints _        -> True
  Products vars -> all (enumerable_var spec) vars
  AnyString     -> False
  AnyInt        -> False
  Time          -> False
  where enumerable_var :: Spec -> Var -> Bool
        enumerable_var spec v = case fmap domain (find_decl spec (remove_decoration spec v)) of
          Nothing   -> False
          Just dom  -> enumerable spec dom

closed_type :: Spec -> DomId -> Maybe Bool
closed_type spec d = fmap closed (find_decl spec d)

type Arguments  = Either [Term] [Modifier]

data Modifier   = Rename Var Term -- with var instantiated instead as the value of expr
                deriving (Ord, Eq, Show, Read)

data Kind       = Fact FactSpec | Act ActSpec | Duty DutySpec | Event EventSpec
                deriving (Ord, Eq, Show, Read)

data Restriction = VarRestriction | FunctionRestriction
                 deriving (Ord, Eq, Show, Read, Enum)

data TypeSpec   = TypeSpec {
                      kind  :: Kind
                    , domain :: Domain
                    , domain_constraint :: Term
                    , restriction :: Maybe Restriction
                    , derivation :: [Derivation]
                    , closed :: Bool {- whether closed world assumption is made for this type -}
                    , conditions  :: [Term]
                    } deriving (Eq, Ord, Show, Read)

data Derivation = Dv [Var] Term
                | HoldsWhen Term
                deriving (Ord, Eq, Show, Read)

data FactSpec   = FactSpec {
                      invariant :: Bool -- TODO move to outer AST
                    , actor     :: Bool
                    }
                deriving (Ord, Eq, Show, Read)

data DutySpec   = DutySpec {
                      enforcing_acts    :: [DomId] -- for record-keeping only, semantics in static-eval
                    , terminating_acts  :: [DomId] -- for record-keeping only, semantics in static-eval
                    , creating_acts     :: [DomId] -- for record-keeping only, semantics in static-eval
                    , violated_when     :: [Term] 
                    }
                deriving (Ord, Eq, Show, Read)

data ActSpec    = ActSpec {
                      effects     :: [Effect]
                    , syncs       :: [Sync]
                    , physical    :: Bool 
                    }
                deriving (Ord, Eq, Show, Read)

physical_acts :: Spec -> M.Map DomId TypeSpec 
physical_acts = M.filter isPhysical . decls
 where isPhysical tspec = case kind tspec of
        Act aspec -> physical aspec 
        _         -> False 

data Effect     = CAll  [Var] Term
                | TAll  [Var] Term
                | OAll  [Var] Term
                deriving (Ord, Eq, Show, Read)

data Sync       = Sync [Var] Term
                deriving (Ord, Eq, Show, Read)

data EventSpec  = EventSpec { 
                      event_effects :: [Effect]
                    , event_syncs   :: [Sync] 
                    }
                deriving (Ord, Eq, Show, Read)

data Spec       = Spec {
                    decls       :: M.Map DomId TypeSpec
                  , aliases     :: M.Map DomId DomId
                  }
                deriving (Eq, Ord, Show, Read)

-- | Union of specifications with overrides/replacements, not concretizations
spec_union :: Spec -> Spec -> Spec
spec_union old_spec new_spec = 
  Spec {decls = decls_union (decls old_spec) (decls new_spec)
       ,aliases = aliases_union (aliases old_spec) (aliases new_spec)
       }

-- | Right-based union over type declarations, only replacement, no concretization
decls_union :: M.Map DomId TypeSpec -> M.Map DomId TypeSpec -> M.Map DomId TypeSpec
decls_union old new = M.union new old

aliases_union :: M.Map DomId DomId -> M.Map DomId DomId -> M.Map DomId DomId
aliases_union old new = M.union new old

emptySpec :: Spec
emptySpec = Spec { decls = built_in_decls, aliases = M.empty}
  where built_in_decls = M.fromList [
                            ("int", int_decl)
                          , ("string", string_decl)
                          , ("actor", actor_decl)
                          ]
basic :: Spec -> S.Set DomId 
basic spec = M.foldrWithKey op S.empty (decls spec)
  where op d tspec res | null (derivation tspec) = S.insert d res
                       | otherwise               = res 

derived :: Spec -> S.Set DomId 
derived spec = M.foldrWithKey op S.empty (decls spec)
  where op d tspec res | null (derivation tspec) = res 
                       | otherwise               = S.insert d res

restriction_of :: Spec -> DomId -> Maybe Restriction
restriction_of spec d = join $ fmap restriction (M.lookup d (decls spec))

-- type-environment pairs, restricting either:
-- * the components of the initial state (all instantiations of <TYPE> restricted by <ENV>)
--    (can be thought of as the Genesis transition, constructing the Garden of Eden)
-- * the possible actions performed in a state, only the actions <TYPE> are enabled 
--    if they are consistent with <ENV>
type Initialiser= [Effect] 

emptyInitialiser :: Initialiser
emptyInitialiser = []

data Statement  = Trans [Var] TransType (Either Term (DomId, Arguments)) -- foreach-application that should evaluate to exactly one act
                | Query Term
                deriving (Show)

data TransType  = Trigger | AddEvent | RemEvent | ObfEvent
                deriving (Ord, Eq, Enum)

type Scenario   = [Statement]

data Directive = Include FilePath
               | Require FilePath

data Phrase = PDo Tagged
            | PTrigger [Var] Term
            | Create [Var] Term
            | Terminate [Var] Term
            | Obfuscate [Var] Term
            | PQuery Term
            | PInstQuery Bool {- whether requested instances must hold true -} [Var] Term
            | PDeclBlock [Decl]
            | PParBlock [Phrase]
            | PSkip
            deriving (Eq, Show, Read)

data Decl = TypeDecl DomId TypeSpec
          | TypeExt DomId [ModClause]
          | PlaceholderDecl DomId DomId 
          deriving (Eq, Show, Read)

data CDecl = CTypeDecl DomId TypeSpec
           | CTypeExt DomId [CModClause]
           | CPlaceholderDecl DomId DomId 
           deriving (Eq, Show, Read)

extend_spec :: [Decl] -> Spec -> Spec
extend_spec = flip (foldr op)
         where op (TypeDecl ty tyspec) spec = spec { decls = M.insert ty tyspec (decls spec) }
               op (PlaceholderDecl f t) spec = spec { aliases = M.insert f t (aliases spec) }
               op _ spec = spec

data ModClause = ConditionedByCl [Term]
               | DerivationCl [Derivation]
               | PostCondCl [Effect]
               | SyncCl [Sync]
               | ViolationCl [Term]
               | EnforcingActsCl [DomId]
               | TerminatedByCl [DomId]
               | CreatedByCl [DomId]
               | StringsCl [String]
               | IntsCl [Int]
               deriving (Eq, Show, Read)

data CModClause = CConditionedByCl [Term]
                | CDerivationCl [Derivation]
                | CPostCondCl [Effect]
                | CSyncCl [Sync]
                | CViolationCl [Term]
                | CEnforcingActsCl [DomId]
                | CTerminatedByCl [DomId]
                | CCreatedByCl [DomId]
                | CStringsCl [String]
                | CIntsCl [Int]
                deriving (Eq, Show, Read)

enforcing_act_condition :: DomId  {- act id -}-> Term
enforcing_act_condition a = Enabled (App a (Right []))

terminated_by_condition :: DomId {- duty id -} -> DomId {- act id -} -> Term
terminated_by_condition d a = App d (Right [])

terminated_by_precondition :: DomId {- duty id -} -> DomId {- act id -} -> Term
terminated_by_precondition d a = Present (App d (Right []))

created_by_condition :: DomId {- duty id -} -> DomId {- act id -} -> Term
created_by_condition d a = App d (Right [])

apply_type_ext :: DomId -> [CModClause] -> TypeSpec -> TypeSpec
apply_type_ext ty clauses tspec = foldr apply_clause tspec clauses 
 where apply_clause clause tspec = case clause of 
        CConditionedByCl conds -> tspec { conditions = conds ++ conditions tspec }
        CDerivationCl dvs -> tspec { derivation = dvs ++ derivation tspec }
        CPostCondCl effs -> tspec { kind = add_effects (kind tspec) }
          where add_effects (Act aspec) = Act (aspec { effects = effs ++ effects aspec})
                add_effects (Event espec)= Event (espec { event_effects = effs ++ event_effects espec })
                add_effects s = s
        CSyncCl ss -> tspec { kind = add_syncs (kind tspec) }
         where add_syncs (Act aspec) = Act $ aspec { syncs = ss ++ syncs aspec} 
               add_syncs (Event espec) = Event $ espec { event_syncs = ss ++ event_syncs espec} 
               add_syncs s = s
        CViolationCl vs -> tspec { kind = add_viol_conds (kind tspec) }
         where add_viol_conds (Duty dspec) = Duty $ dspec { violated_when = vs ++ violated_when dspec }
               add_viol_conds s = s
        CEnforcingActsCl ds -> tspec { kind = add_enf_acts (kind tspec) }
         where add_enf_acts (Duty dspec) = Duty $ dspec { enforcing_acts = ds ++ enforcing_acts dspec }
               add_enf_acts s = s
        CTerminatedByCl as -> tspec { kind = add_terms_acts (kind tspec) }
          where add_terms_acts (Duty dspec) = Duty $ dspec { terminating_acts = as ++ terminating_acts dspec }
                add_terms_acts s = s
        CCreatedByCl as -> tspec { kind = add_create_acts (kind tspec) }
          where add_create_acts (Duty dspec) = Duty $ dspec { creating_acts = as ++ creating_acts dspec }
                add_create_acts s = s
        CStringsCl ss -> tspec { domain = add_strings (domain tspec) }
          where add_strings AnyString     = Strings ss
                add_strings (Strings ss') = Strings (ss' ++ ss)
                add_strings d             = d
        CIntsCl is -> tspec { domain = add_ints (domain tspec) }
          where add_ints AnyInt     = Ints is
                add_ints (Ints is') = Ints (is' ++ is)
                add_ints d          = d

data CPhrase = CDo Tagged            -- execute computed instance
             | CTrigger [Var] Term   -- execute instance to be computed
             | CCreate [Var] Term
             | CTerminate [Var] Term
             | CObfuscate [Var] Term
             | CQuery Term
             | CInstQuery Bool {- whether generated instances must be present -} [Var] Term
             | CPOnlyDecls -- declarations have been removed during static eval
             | CPSkip
             | CPPar CPhrase CPhrase

invariants :: Spec -> S.Set DomId
invariants spec = foldr op S.empty (M.assocs (decls spec))
 where op (ty,tspec) acc = case kind tspec of
         Fact fspec | invariant fspec -> S.insert ty acc
         _ -> acc

actors :: Spec -> S.Set DomId
actors spec = foldr op S.empty (M.assocs (decls spec))
 where op (ty,tspec) acc = case kind tspec of
         Fact fspec | actor fspec -> S.insert ty acc
         _ -> acc

type Subs       = M.Map Var Tagged

data Term       = Not Term
                | And Term Term
                | Or Term Term
                | BoolLit Bool

                | Leq Term Term
                | Geq Term Term
                | Ge Term Term
                | Le Term Term

                | Sub Term Term
                | Add Term Term
                | Mult Term Term
                | Mod Term Term
                | Div Term Term
                | IntLit Int

                | StringLit String

                | Eq Term Term
                | Neq Term Term

                | Exists [Var] Term
                | Forall [Var] Term
                | Count [Var] Term
                | Sum [Var] Term 
                | Max [Var] Term
                | Min [Var] Term
                | When Term Term 
                | Present Term
                | Violated Term
                | Enabled Term
                | Project Term Var

                | Tag Term DomId -- should perhaps not be exposed to the user, auxiliary
                | Untag Term     -- auxiliary
                | Ref Var
                | App DomId Arguments 
                | CurrentTime
                deriving (Show, Ord, Eq, Read)

data Value      = ResBool Bool
                | ResString String
                | ResInt Int
                | ResTagged Tagged
                 deriving (Eq, Show)

data Type       = TyStrings
                | TyInts
                | TyBool
                | TyTagged DomId
                deriving (Eq, Show)

instance Show TransType where
  show Trigger  = ""
  show AddEvent = "+"
  show RemEvent = "-"
  show ObfEvent = "~"

-- instance Show Elem where
--   show v = case v of
--     String s    -> show s
--     Int i       -> show i
--     Product cs  -> "(" ++ intercalate "," (map show_component cs) ++ ")"

-- instance Show Domain where
--   show r = case r of
--     Time          -> "<TIME>"
--     AnyString     -> "<STRING>" 
--     Strings ss    -> "<STRING:" ++ intercalate "," (map show ss) ++ ">"
--     AnyInt        -> "<INT>"
--     Ints is       -> "<INT:" ++ intercalate "," (map show is) ++ ">"
--     Products rs   -> "(" ++ intercalate " * " (map show rs) ++ ")"

-- instance Show Modifier where
--   show (Rename dt1 dt2) = show dt1 ++ " = " ++ show dt2

-- instance Show Var where
--   show (Var ty dec) = ty ++ dec

no_decoration :: DomId -> Var
no_decoration ty = Var ty "" 

remove_decoration :: Spec -> Var -> DomId
remove_decoration spec (Var dom _) = chase_alias spec dom 

duty_decls :: Spec -> [(DomId, DutySpec)]
duty_decls spec = concatMap op $ M.assocs (decls spec)
  where op (d,tspec) = case kind tspec of 
                    Duty ds -> [(d,ds)]
                    _      -> []

trigger_decls :: Spec -> [(DomId, Either EventSpec ActSpec)]
trigger_decls spec = concatMap op $ M.assocs (decls spec)
  where op (d,tspec) = case kind tspec of 
                    Event e -> [(d,Left e)]
                    Act a   -> [(d,Right a)]
                    _       -> []

triggerable :: Spec -> DomId -> Bool
triggerable spec d = case fmap kind (find_decl spec d) of
   Nothing        -> False
   Just (Act _)   -> True
   Just (Event _) -> True 
   Just _         -> False

find_decl :: Spec -> DomId -> Maybe TypeSpec
find_decl spec d = M.lookup (chase_alias spec d) (decls spec)

find_violation_cond :: Spec -> DomId -> Maybe [Term]
find_violation_cond spec d = case M.lookup (chase_alias spec d) (decls spec) of
  Nothing -> Nothing 
  Just ts -> case kind ts of 
    Duty ds -> Just $ violated_when ds
    _       -> Nothing 

chase_alias :: Spec -> DomId -> DomId
chase_alias spec d = chase_alias' S.empty d
  where chase_alias' tried d 
          | d `S.member` tried = d
          | otherwise = maybe d (chase_alias' (S.insert d tried)) (M.lookup d (aliases spec))

show_arguments :: Arguments -> String
show_arguments (Right mods) = show_modifiers mods
show_arguments (Left xs) = "(" ++ intercalate "," (map show xs) ++ ")"

show_modifiers :: [Modifier] -> String
show_modifiers [] = "()"
show_modifiers cs = "(" ++ intercalate "," (map show cs) ++ ")"

show_projections :: [Var] -> String
show_projections [] = ""
show_projections ds = "[" ++ intercalate "," (map show ds) ++ "]"

show_component :: Tagged -> String
show_component = ppTagged 

ppTagged :: Tagged -> String
ppTagged (v,t) = case v of 
  String s    -> t ++ "(" ++ show s ++ ")"
  Int i       -> t ++ "(" ++ show i ++ ")"
  Product tes -> t ++ "(" ++ intercalate "," (map ppTagged tes) ++ ")"


show_stmt :: Statement -> String
show_stmt (Query t) = "?" ++ show t 
show_stmt (Trans xs atype etm) = case xs of 
  [] -> case etm of Left t         -> show atype ++ show t
                    Right (d,mods) -> show atype ++ d ++ show_arguments mods 
  _  -> "(" ++ "Foreach " ++ intercalate "," (map show xs) ++ " : " ++ show_stmt (Trans [] atype etm) ++ ")"

valOf :: Tagged -> Elem
valOf (c,t) = c

tagOf :: Tagged -> DomId
tagOf (c,t) = t

substitutions_of :: [Modifier] -> [(Var, Term)]
substitutions_of = map (\(Rename x y) -> (x,y)) 

make_substitutions_of :: [Var] -> Arguments -> [(Var, Term)] 
make_substitutions_of _ (Right mods) = substitutions_of mods
make_substitutions_of xs (Left args) = zip xs args

project :: Tagged -> DomId -> Maybe Tagged
project (Product tvs,_) ty = asum (map try tvs)
  where try tv@(v,ty') | ty == ty' = Just tv
        try _                        = Nothing
project _ _ = Nothing

-- environments

emptySubs :: Subs
emptySubs = M.empty

-- | right-biased
subsUnion :: Subs -> Subs -> Subs
subsUnion = flip M.union

subsUnions :: [Subs] -> Subs
subsUnions = foldr subsUnion M.empty

{-
subsUnify :: Subs -> Subs -> Bool 
subsUnify e1 = M.foldrWithKey op True 
  where op k v res | Just v' <- M.lookup k e1, v /= v' = False
                   | otherwise                         = res
-}

-- functions related to partial instantiation (refinement)

type Refiner = M.Map DomId Domain

emptyRefiner :: Refiner
emptyRefiner = M.empty

refine_specification :: Spec -> Refiner -> Spec
refine_specification spec rm = 
  spec { decls = M.foldrWithKey reinserter (decls spec) (decls spec) }
  where reinserter k tspec sm' = case M.lookup k rm of 
          Nothing -> sm'
          Just d  -> case (d, domain tspec) of 
            (Strings ss, AnyString)   -> sm''
            (Strings ss, Strings ss') 
              | all (`elem` ss') ss   -> sm''
            (Ints is, AnyInt)         -> sm''
            (Ints is, Ints is')
              | all (`elem` is') is   -> sm''
            _ -> sm'
            where sm'' = M.insert k (tspec {domain = d}) sm'

actor_decl :: TypeSpec
actor_decl = TypeSpec { kind = Fact (FactSpec False True)
                      , domain = AnyString 
                      , domain_constraint = BoolLit True
                      , restriction = Nothing
                      , derivation = [] 
                      , conditions = []
                      , closed = True
                      }

int_decl :: TypeSpec
int_decl = TypeSpec {  kind = Fact (FactSpec False False) 
                    ,  domain = AnyInt
                    ,  domain_constraint = BoolLit True
                    ,  restriction = Nothing
                    ,  derivation = []
                    ,  closed = True  
                    ,  conditions = [] } 

ints_decl :: [Int] -> TypeSpec
ints_decl is = int_decl { domain = Ints is } 

string_decl :: TypeSpec
string_decl = TypeSpec  {  kind = Fact (FactSpec False False)
                        ,  domain = AnyString
                        ,  domain_constraint = BoolLit True
                        ,  restriction = Nothing
                        ,  derivation = [] 
                        ,  closed = True 
                        ,  conditions = [] }

strings_decl :: [String] -> TypeSpec
strings_decl ss = 
  TypeSpec  { kind = Fact (FactSpec False False)
            , domain = Strings ss
            , domain_constraint = BoolLit True
            , restriction = Nothing
            , derivation = [] 
            , closed = True 
            , conditions = [] }

newtype TaggedJSON = TaggedJSON Tagged

instance ToJSON TaggedJSON where
  toJSON (TaggedJSON te@(v,d)) = case v of 
    String s    -> object [ "tagged-type" .= JSON.String "string", "fact-type" .= toJSON d, "value" .= toJSON s, "textual" .= toJSON (ppTagged te) ]
    Int i       -> object [ "tagged-type" .= JSON.String "int", "fact-type" .= toJSON d, "value" .= toJSON i, "textual" .= toJSON (ppTagged te)  ]
    Product tes -> object [ "tagged-type" .= JSON.String "product", "fact-type" .= toJSON d, "arguments" .= toJSON (map TaggedJSON tes), "textual" .= toJSON (ppTagged te) ]
