{-# LANGUAGE TupleSections #-}

module Language.EFLINT.Explorer where

import Language.EFLINT.Spec (Spec, Phrase(PSkip), ppTagged)
import Language.EFLINT.State (State, TransInfo(..), Assignment(..), trans_is_action)
import Language.EFLINT.Interpreter (Program(..), Config(..), interpreter, initialConfig, Output, getOutput)
import Language.EFLINT.Print()

import qualified Language.Explorer.Pure as EI
import Language.Explorer.Monadic (revert, jump)

import Data.Tree (drawTree, Tree(..))

type Explorer = EI.Explorer Label Config [Output]

type Label = Program

data Instruction = Execute [Program] 
                 | ExecuteOnce Program
                 | Revert Ref Bool {- whether the revert is destructive or not -} 
                 | Display Ref  -- `last' edge leading to given ref
                 | DisplayFull Ref -- full `history', see `Path' below, for given ref
                 | ExplorationHeads -- nodes in the execution graph without outgoing edges
                 | CreateExportExploration -- create export data to recreate execution graph
                 | LoadExportExploration ExecutionGraph -- load execution graph
data Response    = ResultTrans Explorer [Output] (Config, Ref) (Config, Ref)
                 | Path Path
                 | Nodes [Node]
                 | InvalidRevert
                 | ExportExploration ExecutionGraph
                 | LoadExploration Explorer

type Ref = Int -- state identifier
type Path = [(Node, (Label, [Output]), Node)] 
type Node = (Ref, Config)

data N = N {
           ref :: Ref
         , config :: Config
         }  
         deriving (Eq)

data Edge = Edge {
            source :: Ref
          , target :: Ref
          , po     :: PO
          }  
          deriving (Eq)

data PO = PO {
          label  :: Label 
        , output :: [Output]
        }  
        deriving (Eq)

data ExecutionGraph = ExecutionGraph {
                      current :: Ref
                    , nodes   :: [N]
                    , edges   :: [Edge]
                    }

showTree :: Explorer -> String
showTree = drawTree . fmap (("#"++) . show . fst) . EI.toTree

showTriggerTree :: TransInfo -> String
showTriggerTree = drawTree . fmap report . triggerTree
  where report info = ppTagged (trans_tagged info) ++ " " ++ whether_enabled 
--                      ++ "\n" ++ unlines (map (uncurry mod) (M.assocs (trans_assignments info)))
         where mod te ass = case ass of  HoldsTrue -> "+" ++ ppTagged te
                                         HoldsFalse -> "-" ++ ppTagged te
                                         Unknown -> "~" ++ ppTagged te
               whether_enabled | not (trans_is_action info) = ""
                               | trans_forced info          = "(DISABLED)"
                               | otherwise                  = "(ENABLED)"

triggerTree :: TransInfo -> Tree TransInfo 
triggerTree t = Node t (map triggerTree (trans_syncs t))

get_last_edge :: Explorer -> Ref -> ((Ref, Config), (Label, [Output]), (Ref, Config))
get_last_edge exp cr = case reverse (EI.getPathFromTo exp 1 cr) of
  (edge:_) -> edge 
  _ -> maybe (error ("ASSERT: get_last_edge1")) (\cfg -> ((cr,cfg), ((Program PSkip),[]), (cr,cfg))) (EI.deref exp cr) 
        
init_tree_explorer, init_graph_explorer :: Maybe (Spec,State) -> Explorer
init_tree_explorer = EI.mkExplorer False (const . const $ False) defInterpreter . initialConfig
init_graph_explorer = EI.mkExplorer True (==) defInterpreter . initialConfig

defInterpreter p c = getOutput $ interpreter p c

run_ :: Explorer -> Instruction -> Response
run_ exp instr = case instr of 
  Execute ps -> 
    let (exp',outs) = EI.executeAll ps exp
        cfg'        = EI.config exp'
        ref'        = EI.currRef exp'
    in ResultTrans exp' outs (EI.config exp, EI.currRef exp) (cfg', ref')
  ExecuteOnce ps -> 
    let (exp',outs) = EI.execute ps exp
        cfg'        = EI.config exp'
        ref'        = EI.currRef exp'
    in ResultTrans exp' outs (EI.config exp, EI.currRef exp) (cfg', ref')
  Revert r d -> case (if d then revert else jump) r exp of 
    Nothing   -> InvalidRevert
    Just exp'  -> ResultTrans exp' [] (EI.config exp, EI.currRef exp) (EI.config exp', EI.currRef exp')
  Display id -> ResultTrans exp out (from, pr) (to, cr)
    where ((pr,from), (_,out), (cr, to)) = get_last_edge exp id
  DisplayFull id -> Path $ EI.getPathFromTo exp 1 id
  ExplorationHeads -> Nodes $ EI.leaves exp
  CreateExportExploration -> ExportExploration $ convertToGraph (EI.toExport exp)
  LoadExportExploration graph -> LoadExploration $ EI.fromExport exp (convertFromGraph graph)

convertToGraph :: (Ref, [(Ref, Config)], [(Ref, Ref, (Label, [Output]))]) -> ExecutionGraph
convertToGraph (cid, nodes, edges) = ExecutionGraph{current=cid, nodes=(map convertToN nodes), edges=(map convertToEdges edges)}

convertFromGraph :: ExecutionGraph -> (Ref, [(Ref, Config)], [(Ref, Ref, (Label, [Output]))])
convertFromGraph graph = (current graph, map convertFromN (nodes graph), map convertFromEdges (edges graph))

convertToN :: (Ref, Config) -> N
convertToN (r, c) = N{ref=r, config=c}

convertFromN :: N -> (Ref, Config) 
convertFromN n = (ref n, config n)

convertToEdges :: (Ref, Ref, (Label, [Output])) -> Edge
convertToEdges (sid, tid, (p, o)) = Edge{source=sid, target=tid, po=PO{label=p, output=o}}

convertFromEdges :: Edge -> (Ref, Ref, (Label, [Output]))
convertFromEdges edge = (source edge, target edge, convertFromPO (po edge))

convertFromPO :: PO -> (Label, [Output])
convertFromPO po = (label po, output po)
