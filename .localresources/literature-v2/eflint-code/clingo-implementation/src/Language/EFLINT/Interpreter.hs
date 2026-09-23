{-# LANGUAGE RecordWildCards, LambdaCase #-}

module Language.EFLINT.Interpreter (Config(..), Program(..), interpreter, initialConfig, rest_disabled, rest_enabled, get_transition, context2config, make_initial_state
                   ,OutputWriter, Output(..), getOutput
                   ,errors, violations, ex_triggers, query_ress, inst_query_ress, missing_inputs
                   ,missing_assignments, missing_instances_for
                   ,convert_programs, collapse_programs) where

import Language.EFLINT.Eval
import Language.EFLINT.Spec
import Language.EFLINT.Saturation
import Language.EFLINT.StaticEval (compile_phrase, runStatic) 
import Language.EFLINT.State

import Control.Monad (forM, forM_, when)
import Control.Monad.Writer (Writer, tell, runWriter)
import Control.Applicative (empty)

import qualified Data.Map as M
import qualified Data.Set as S

data Program = Program Phrase 
             | PSeq Program Program
             | ProgramSkip
             deriving (Eq, Show)

data Config = Config {
        cfg_spec          :: Spec
      , cfg_state         :: State 
      , rest_transitions  :: [Transition] -- (label * enabled?) -- replaced
      , rest_duties       :: [Tagged] -- replaced after ever step
      }
      deriving (Eq)

data Output = ErrorVal Error
            | ExecutedTransition TransInfo 
            | Violation Violation
            | QueryRes QueryRes -- whether query succeed or not 
            | InstQueryRes [Tagged]
            deriving (Eq, Show, Read)

convert_programs :: [Phrase] -> [Program]
convert_programs phrases = map Program phrases

collapse_programs :: [Program] -> Program
collapse_programs [] = ProgramSkip
collapse_programs programs = (foldr1 PSeq programs)

interpreter :: Program -> Config -> OutputWriter (Maybe Config)
interpreter (Program p) cfg = case runStatic (compile_phrase p) (ctx_spec ctx) of
    Left err  -> tell [ErrorVal (CompilationError (unlines err))] >> return Nothing 
    Right (spec', p') -> sem_phrase p' (ctx{ctx_spec = spec'}) >>= \case
        Nothing -> return Nothing
        Just sto  -> fmap context2config <$> new_context spec' (ctx_state ctx) sto
  where ctx = config2context cfg
interpreter (PSeq p1 p2) cfg = (interpreter p1 cfg) >>= interpreter p2 . maybe cfg id
interpreter (ProgramSkip) cfg = return Nothing

initialConfig Nothing = context2config (emptyContext emptySpec)
initialConfig (Just (spec,state)) = context2config $
  (emptyContext spec) { ctx_state = state }

context2config :: Context -> Config
context2config ctx = Config {
    cfg_spec    = ctx_spec ctx
  , cfg_state   = ctx_state ctx
  , rest_transitions = ctx_transitions ctx
  , rest_duties      = ctx_duties ctx
  }

config2context :: Config -> Context
config2context cfg = Context {
    ctx_spec = cfg_spec cfg
  , ctx_state = cfg_state cfg
  , ctx_transitions = []
  , ctx_duties = []
  }

rest_enabled = map fst . filter snd . map get_transition . rest_transitions
rest_disabled = map fst . filter (not . snd) . map get_transition . rest_transitions

get_transition :: Transition -> (Tagged, Bool)
get_transition transition = (tagged transition, exist transition)

ex_triggers :: [Output] -> [TransInfo]
ex_triggers = concatMap op
 where op (ExecutedTransition out) = [out]
       op _ = []

violations :: [Output] -> [Violation]
violations = concatMap op
 where op (Violation v) = [v]
       op _ = []

errors :: [Output] -> [Error]
errors = concatMap op
  where op (ErrorVal err) = [err]
        op _ = []

query_ress :: [Output] -> [QueryRes]
query_ress = concatMap op
  where op (QueryRes b) = [b]
        op _ = []

inst_query_ress :: [Output] -> [[Tagged]]
inst_query_ress = concatMap op
  where op (InstQueryRes vs) = [vs]
        op _                 = []

missing_inputs :: [Output] -> [MissingInput]
missing_inputs = S.toList . S.fromList . concatMap op
  where op (ErrorVal (RuntimeError (MissingInput miss))) = [miss]
        op _ = []

missing_instances_for :: [MissingInput] -> [(DomId, MDomain, Maybe Restriction)]
missing_instances_for = concatMap op
  where op (MissingAssignments tes _)     = [] 
        op (MissingInstances d dom mres)  = [(d,dom,mres)]

type OutputWriter = Writer [Output]

getOutput :: OutputWriter a -> (a,[Output])
getOutput = runWriter

do_saturation :: Spec -> State -> OutputWriter (Maybe State)
do_saturation spec state = case runSubs (rebase_and_sat spec state) spec state emptySubs of
  Right [state'] -> return (Just state')
  Right _        -> error "assert do_saturation: no or ambiguous saturation result"
  Left err       -> tell [ErrorVal $ RuntimeError err] >> return Nothing

error_or_process :: M_Subs a -> Spec -> State -> ([a] -> OutputWriter (Maybe b)) -> OutputWriter (Maybe b)
error_or_process ma spec state fa = case runSubs ma spec state emptySubs of
  Left err  -> tell [ErrorVal $ RuntimeError err] >> return Nothing
  Right as  -> fa as

new_context :: Spec -> State -> Store -> OutputWriter (Maybe Context)
new_context spec state ass = do_saturation spec (make_assignments spec ass state) >>= \case
 Nothing -> return Nothing
 Just state' -> do 
  let duties = [ te | te@(v,d) <- (state_holds state')
                    , Duty _ <- maybe [] (:[]) (fmap kind (find_decl spec d)) ]
  error_or_process (find_duty_violations duties) spec state' $ \d_viols -> 
    error_or_process (find_inv_violations (S.toList $ invariants spec)) spec state' $ \i_viols -> do
      tell (map Violation (concat d_viols ++ concat i_viols)) 
      error_or_process find_transitions spec state' $ \tss ->  
        return $ Just $ Context
          { ctx_state = state'
          , ctx_spec = spec 
          , ctx_transitions = concat tss
          , ctx_duties = duties 
          }


sem_phrase :: CPhrase -> Context -> OutputWriter (Maybe Store)
sem_phrase p c0 = case p of
  CPSkip   -> return Nothing
  CPOnlyDecls -> no_effect 
  CQuery t -> error_or_process (eval t) spec state $ \vs -> do  
                 let queryRes | all (== (ResBool True)) vs = QuerySuccess
                              | otherwise                  = QueryFailure
                 tell [QueryRes queryRes] >> no_effect
  CInstQuery b vs t -> 
    let t' | b         = When t (Present t)
           | otherwise = t
    in error_or_process (foreach vs (whenTagged (eval t') return)) spec state $ \vs -> 
                      tell [InstQueryRes (concat vs)] >> no_effect
  CCreate vs t    -> single_effect (CAll vs t)
  CTerminate vs t -> single_effect (TAll vs t)
  CObfuscate vs t -> single_effect (OAll vs t)
  CDo te          -> error_or_process (trigger_or_fail te) spec state consider_transinfos
  CTrigger vs t -> let m_subs = do  
                        tes <- foreach vs (whenTagged (eval t) return)
                        case tes of 
                         (te@(_,d):_) | triggerable spec d -> Right <$> forM tes instantiate_trans 
                                      | otherwise -> return (Left d)
                         _ -> return (Right [])
                     in error_or_process m_subs spec state consider_transinfos
  CPPar p1 p2 -> do mc1 <- sem_phrase p1 c0
                    mc2 <- sem_phrase p2 c0
                    case (mc1, mc2) of 
                      (Just c1, Just c2) -> return (Just $ c1 `store_union` c2)
                      _                  -> return Nothing
--                      (Just c1, Nothing) -> return mc1
--                      (Nothing, Just c2) -> return mc2
--                      (Nothing, Nothing) -> return Nothing 
  where spec = ctx_spec c0
        state = ctx_state c0

        no_effect :: OutputWriter (Maybe Store)
        no_effect = return $ Just emptyStore 

        single_effect :: Effect -> OutputWriter (Maybe Store)
        single_effect eff =
          error_or_process (eval_effect eff) spec state $ \stores ->
            return (Just $ M.unions stores) {- always just one store-} 

        trigger_or_fail :: Tagged -> M_Subs (Either DomId [TransInfo])
        trigger_or_fail te@(_,d) | triggerable spec d = Right . (:[]) <$> instantiate_trans te
                                 | otherwise          = return $ Left d 

        consider_transinfos [Left d] = tell [ErrorVal (NotTriggerable d)] >> no_effect
        consider_transinfos [Right infos] = do
          forM_ infos $ \info -> do  tell [ExecutedTransition info]
                                     tell_violations info
          return (Just $ store_unions (map trans_assignments infos)) 
        consider_transinfos _ = error "ASSERT: consider_transinfos"

tell_violations :: TransInfo -> OutputWriter ()
tell_violations info 
  | trans_is_action info = 
      -- report whether this action is violated (potentially caused by any successor)
      -- if not violated, then so will not any successor
      when (trans_forced info) (tell [Violation (TriggerViolation info)]) >> mapM_ tell_violations (trans_syncs info)
  | otherwise = 
      -- report whether successors are violated, given that they could be actions
      mapM_ tell_violations (trans_syncs info) 

find_inv_violations :: [DomId] -> M_Subs [Violation]
find_inv_violations ds = do 
  spec <- get_spec 
  (concat <$>) $ forM ds $ \d -> results $ do
    let term = Exists [Var d ""] (Present (Ref (Var d "")))
    ignoreMissingInput (checkFalse (eval term))
    return (InvariantViolation d)

find_duty_violations :: [Tagged] -> M_Subs [Violation]
find_duty_violations tes = do 
  spec <- get_spec 
  (concat <$>) $ forM tes $ \te@(_,d) -> results $ do
    ignoreMissingInput (eval_violation_condition te (find_violation_cond spec d)) >>= \case 
      True  -> return (DutyViolation te)
      False -> empty 
 
find_transitions :: M_Subs [Transition]
find_transitions = do
  spec <- get_spec 
  concat <$> mapM gen_trans (trigger_decls spec)
  where gen_trans (d,_) = results $ ignoreMissingInput $ do
          tagged <- every_possible_subs (no_decoration d)
          exist  <- is_holds tagged
          return Transition{..}

every_possible_subs :: Var -> M_Subs Tagged
every_possible_subs x = do
    spec <- get_spec
    let d = remove_decoration spec x
    (dom, _) <- get_dom d
    if enumerable spec dom then generate_instances d
                           else every_available_subs d
 where generate_instances d = do
          (dom, dom_filter) <- get_dom d
          e <- instantiate_domain d dom
          let bindings = case (dom,e) of (Products xs, Product args) -> M.fromList (zip xs args)
                                         _ -> M.singleton (no_decoration d) (e,d) 
          modify_subs (`subsUnion` bindings) (checkTrue (eval dom_filter))
          return (e,d)
       every_available_subs d = do
          (dom, dom_filter) <- get_dom d
          case dom of
            Products xs -> do
              args <- sequence (map every_possible_subs xs)
              modify_subs (`subsUnion` (M.fromList (zip xs args))) (checkTrue (eval dom_filter))
              return (Product args, d)
            _ -> do
              state <- get_state
              nd $  [ te | te@(v,d') <- state_holds state, d' == d ]

make_initial_state :: Spec -> Initialiser -> State
make_initial_state spec inits = 
  let make_inits = do 
        sto <- store_unions <$> mapM eval_effect inits
        rebase_and_sat spec (make_assignments spec sto emptyState)
  in case runSubs make_inits spec emptyState emptySubs of
    Left err -> error (print_runtime_error err)
    Right res -> case res of 
      []      -> error "failed to initialise state"
      [state] -> state 
      _       -> error "non-deterministic state initialisation"          
