{-# LANGUAGE TupleSections #-}

module Language.EFLINT.Parse where

import Language.EFLINT.Spec

import GLL.Combinators hiding (many, some, IntLit, BoolLit, StringLit)
import Text.Regex.Applicative hiding ((<**>), optional)

import Data.Char (isLower)
import qualified Data.Map as M

flint_lexer :: String -> Either String [Token]
flint_lexer = lexerEither lexer_settings

lexer_settings :: LexerSettings
lexer_settings = emptyLanguage {
    identifiers = types
  , signed_int_lits = False 
  , keywords =  ["!?","||", "&&", "<=", ">=", "..", "True", "False", "Sum", "==", "!=", "When", "Where","Holds when",  "Holds", "Present when", "Present", "Max", "Min", "Count", "Union", "Enabled", "Violated when", "Violated"
                , "Atom", "String", "Int", "Time", "Current Time"
                , "Exists", "Forall", "Foreach", "Force"
                , "Extend", "Event", "Act", "Fact", "Physical", "Bool", "Var", "Function", "Invariant", "Predicate", "Duty", "Actor", "Holder", "Claimant", "Recipient", "Related to", "Conditioned by", "Creates", "Terminates", "Obfuscates", "Terminated by", "Created by", "With" , "Identified by", "Derived from", "Derived externally", "Enforced by", "Syncs with"
                , "Do", "Placeholder", "For", "Not", "Open", "Closed", "?-", "?--" 
                , "#", "##", "###", "####"
                , "#include", "#require"
                ]
  , keychars = ['[', ']', '(', ')', '!', ',', '\'', '+', '-', '*', '/', '.', '=', '>', '<', ':', '?', '{', '}', '%', '~']
  } 
  where types = (concat .) . (:) <$>  
                word <*> many ((++) <$> (concat <$> some ((:[]) <$> psym (== ' '))) <*> word) <|> 
                (\id -> "[" ++ id ++ "]") <$ sym '[' <*> many internal <* sym ']' <|>
                (\id -> "<" ++ id ++ ">") <$ sym '<' <*> act_or_duty <* sym '>'
          where word = (\c ss -> c:concat ss) <$> psym isLower <*> many ((:[]) <$> psym isLower <|> hyphen <|> ((:[]) <$> sym '_'))
                  where hyphen = (\c1 c2 -> [c1,c2]) <$> sym '-' <*> psym isLower 
                act_or_duty = (\id -> "<" ++ id ++ ">") <$ sym '<' <*> many internal <* sym '>'
                              <|> (:) <$> psym (not . flip elem "< =") <*> many internal 
                internal = psym (\c -> not (c `elem` "]>+="))

value_expr :: BNF Token Term
value_expr = "value-expr"
  <::=  BoolLit True <$$ keyword "True"
  <||>  BoolLit False <$$ keyword "False"
  <||>  When <$$> value_expr <** keyword_when <**> value_expr
  
  <||>  Or <$$> value_expr <** keyword "||" <<<**> value_expr
  <||>  And <$$> value_expr <** keyword "&&" <<<**> value_expr

  <||>  Eq <$$> value_expr <** keyword "==" <**> value_expr
  <||>  Neq <$$> value_expr <** keyword "!=" <**> value_expr

  <||>  Leq <$$> value_expr <** keyword "<="  <<<**> value_expr
  <||>  Geq <$$> value_expr <** keyword ">="  <<<**> value_expr
  <||>  Le  <$$> value_expr <** keychar '<'  <<<**> value_expr
  <||>  Ge  <$$> value_expr <** keychar '>' <<<**> value_expr
  <||>  Sub <$$> value_expr <** keychar '-' <**>>> value_expr 
  <||>  Add <$$> value_expr <** keychar '+' <**>>> value_expr 
  <||>  Mult <$$> value_expr <** keychar '*' <**>>> value_expr 
  <||>  Mod  <$$> value_expr <** keychar '%' <**>>> value_expr 
  <||>  Div <$$> value_expr <** keychar '/' <**>>> value_expr 
  <||>  Not <$$ keychar '!' <**> value_expr 
  <||>  Not <$$ keyword "Not" <**> value_expr 

  <||>  keyword "Sum" **> foreach Sum
  <||>  keyword "Count" **> foreach Count 
  <||>  keyword "Max" **> foreach Max
  <||>  keyword "Min" **> foreach Min

  <||>  IntLit <$$> int_lit
  <||>  StringLit <$$> atom 
  <||>  Ref <$$> var 
  <||>  application App
  <||>  Project <$$> value_expr <** keychar '.' <**> (var <||> parens var)
  <||>  Tag <$$> value_expr <** keychar ':' <**> id_lit 

  <||>  parens (Exists <$$ keyword "Exists" <**> multipleSepBy1 var (keychar ',') <** keychar ':' <**> value_expr)
  <||>  parens (Forall <$$ keyword "Forall" <**> multipleSepBy1 var (keychar ',') <** keychar ':' <**> value_expr)
  <||>  Present <$$ keyword "Present" <**> value_expr
  <||>  Present <$$ keyword "Holds" <**> value_expr
  <||>  Violated <$$ keyword "Violated" <**> value_expr
  <||>  Enabled <$$ keyword "Enabled" <**> value_expr
  <||>  parens value_expr
  <||>  CurrentTime <$$ keyword "Current Time"

keyword_when :: BNF Token String
keyword_when = "when-or-where" <:=> keyword "Where" <||> keyword "When"

var :: BNF Token Var
var = "decorated-type-lit"
  <:=> Var <$$> id_lit <**> decoration

atom :: BNF Token String
atom = "atom" <:=> string_lit <||> alt_id_lit

decoration :: BNF Token String 
decoration = "decoration"
  <:=> make_f <$$> optional int_lit <**> multiple (keychar '\'')
  where make_f mi str = maybe "" show mi ++ str

arguments :: BNF Token Arguments 
arguments = "arguments"
  <:=> parens ( Right <$$> multipleSepBy modifier (keychar ',')
           <||> Left <$$> multipleSepBy1 value_expr (keychar ',') )

modifier :: BNF Token Modifier
modifier = "modifier"
  <:=> Rename <$$> var <** keychar '=' <**> value_expr 

type_expr :: BNF Token Domain
type_expr = "type-expr"
  <::=  Products . (:[]) <$$> var 
  <||>  Strings <$$> manySepBy2 atom (keychar '+' <||> keychar ',')
  <||>  Ints <$$> manySepBy2 int_lit (keychar '+' <||> keychar ',')
  <||>  Products <$$> manySepBy2 var (keychar '*')
  <||>  parens (Products <$$> manySepBy2 var (keychar '*'))
  <||>  Ints . (:[]) <$$> int_lit
  <||>  ints_from_domain <$$> int_lit <** keyword ".." <**> int_lit
  <||>  Strings . (:[]) <$$> atom 
  <||>  strings_from_domain <$$> char_lit <** keyword ".." <**> char_lit
  <||>  AnyString <$$ keyword "String"
  <||>  AnyString <$$ keyword "Atom"
  <||>  AnyInt <$$ keyword "Int"
  <||>  Time <$$ keyword "Time"
  where ints_from_domain :: Int -> Int -> Domain 
        ints_from_domain min max = Ints $ [min..max]

        strings_from_domain :: Char -> Char -> Domain
        strings_from_domain min max = Strings $ map (:[]) [min..max]


-- parsing frame specifications
parse_component :: BNF Token a -> String -> Either String a
parse_component p str = case flint_lexer str of
  Left err  -> Left err
  Right ts  -> case parseWithOptionsAndError [maximumErrors 1] p ts of
   Left err -> Left err
   Right as -> Right (head as)

flint :: BNF Token (Spec, Refiner, Initialiser, Scenario)
flint = "flint" <:=> cons <$$ 
  optional (keyword "#") <**> declarations <**> 
  optionalWithDef (keyword "##" **> refiner) M.empty <**>
  optionalWithDef (keyword "###" **> initialiser) [] <**> 
  optionalWithDef (keyword "####" **> scenario) []
  where cons ds r i s = (extend_spec ds emptySpec, r, i, s)

parse_flint = parse_component flint

declarations :: BNF Token [Decl]
declarations = "declarations" <:=> concat <$$> multiple1 frame 

placeholder :: BNF Token Decl
placeholder = "placeholder-decl" <:=> PlaceholderDecl <$$ keyword "Placeholder" <**> id_lit <** keyword "For" <**> id_lit

frame :: BNF Token [Decl]
frame = "frame" <:=> fact 
                <||> duty 
                <||> act
                <||> physical 
                <||> event 
                <||> (:[]) <$$> syn_ext
                <||> (:[]) <$$> placeholder 
  where fact = syn_fact_decl (make_fact False False)
          <||> syn_bool_fact_decl make_bool_fact 
          <||> syn_pred_decl (make_pred False) 
          <||> syn_inv_decl make_inv 
          where make_fact :: Bool -> Bool -> Bool -> Maybe Restriction -> DomId -> Domain -> Term -> [ModClause] -> [Decl]
                make_fact inv is_actor is_closed restr ty dom dom_filter clauses = 
                 [TypeDecl ty tspec, TypeExt ty clauses]
                 where tspec = TypeSpec  { kind = Fact (FactSpec inv is_actor)
                                         , domain = dom
                                         , domain_constraint = dom_filter
                                         , restriction = restr
                                         , derivation = []
                                         , closed = is_closed
                                         , conditions = [] }
                make_pred inv ty t = make_fact inv False True Nothing ty (Products []) (BoolLit True) [DerivationCl [HoldsWhen t]]
                make_inv ty t = make_pred True ty t
                make_bool_fact is_closed ty clauses = 
                  make_fact False False is_closed Nothing ty (Products []) (BoolLit True) clauses 

        act = syn_act_decl make_act
          where make_act is_closed ty mact mrec attrs dom_filter clauses = 
                  [TypeDecl ty tspec, TypeExt ty clauses]
                 where tspec = TypeSpec {
                        kind = Act (ActSpec {effects = [], syncs = [], physical = False } ),
                        domain = Products (actor:(maybe [] (:[]) mrec ++ attrs)), 
                        domain_constraint = dom_filter,
                        restriction = Nothing, 
                        derivation = [],
                        closed = is_closed, 
                        conditions = [] }
                       actor = maybe (no_decoration "actor") id mact

        physical = syn_physical_decl make_physical
          where make_physical ty mact attrs dom_filter clauses = 
                  [TypeDecl ty tspec, TypeExt ty (holds_true:clauses)]
                 where tspec = TypeSpec {
                        kind = Act (ActSpec { effects = [], syncs = [], physical = True }),
                        domain = Products (actor:attrs),
                        domain_constraint = dom_filter,
                        restriction = Nothing,
                        derivation = [],
                        closed = True,
                        conditions = [] }
                       actor = maybe (no_decoration "actor") id mact
                       holds_true = DerivationCl [HoldsWhen (BoolLit True)]

        event = syn_event_decl make_event 
          where make_event is_closed ty attrs dom_filter clauses =
                 [TypeDecl ty tspec, TypeExt ty clauses]
                 where tspec = TypeSpec {
                          kind = Event (EventSpec { event_effects = [], event_syncs = [] })
                        , domain = Products attrs
                        , domain_constraint = dom_filter
                        , restriction = Nothing
                        , derivation = []
                        , closed = is_closed
                        , conditions = []
                        } 
 
        duty = syn_duty_decl make_duty 
          where make_duty is_closed ty hold claim attrs dom_filter clauses = 
                  [TypeDecl ty tspec, TypeExt ty clauses]
                 where tspec = TypeSpec {
                        domain = Products (hold:claim:attrs),
                        domain_constraint = dom_filter,
                        restriction = Nothing,
                        kind = Duty (DutySpec { violated_when = [], enforcing_acts = []
                                              , terminating_acts = [], creating_acts = [] }), 
                        derivation = [], 
                        closed = is_closed, 
                        conditions = []}

syn_fact_decl :: (Bool -> Maybe Restriction -> DomId -> Domain -> Term -> [ModClause] -> a) -> BNF Token a
syn_fact_decl cons = "fact-type-decl" <:=> cons <$$>
  syn_is_closed <**> fact_restriction_by_keyword <**> id_lit <**>
  optionalWithDef (keyword "Identified by" **> type_expr) AnyString <**>
  syn_domain_constraint <**>>> -- prefers initial Identified by clause over extension (the two are ambiguous if only one Identified by clause is given). NOTE, example of ambiguity where in one case (Strings) the two interpretations are equivalent and in the other cases (Ints) type-checking could resolve the ambiguity
  syn_fact_clauses

fact_restriction_by_keyword :: BNF Token (Maybe Restriction)
fact_restriction_by_keyword = "restricted-fact" <:=> 
                Nothing                   <$$ keyword "Fact"
          <||>  Just VarRestriction       <$$ keyword "Var"
          <||>  Just FunctionRestriction  <$$ keyword "Function"

syn_bool_fact_decl :: (Bool -> DomId -> [ModClause] -> a) -> BNF Token a
syn_bool_fact_decl cons = "bool-fact-type-decl" <:=> cons <$$>
  syn_is_closed <** keyword "Bool" <**> id_lit <**> syn_fact_clauses 

syn_ext :: BNF Token Decl
syn_ext = "type-ext" <:=> 
  keyword "Extend" **> (    syn_fact_ext 
                       <||> syn_act_ext 
                       <||> syn_duty_ext 
                       <||> syn_event_ext )

syn_is_closed :: BNF Token Bool
syn_is_closed = "is-type-closed-modifier" <:=> optionalWithDef alts True
  where alts =     True <$$ keyword "Closed"
              <||> False <$$ keyword "Open"

syn_fact_ext :: BNF Token Decl
syn_fact_ext = "fact-type-ext" <:=> TypeExt <$$ keyword "Fact" <**> id_lit <**> syn_fact_clauses 

syn_pred_decl :: (DomId -> Term -> a) -> BNF Token a
syn_pred_decl cons = "pred-type-decl" <:=> cons <$$ 
  keyword "Predicate" <**> id_lit <** keyword_when <**> value_expr

syn_inv_decl :: (DomId -> Term -> a) -> BNF Token a
syn_inv_decl cons = "inv-type-decl" <:=> cons <$$
  keyword "Invariant" <**> id_lit <** keyword_when <**> value_expr  

syn_domain_constraint = optionalWithDef (keyword_when **> value_expr) (BoolLit True)

syn_duty_decl :: (Bool -> DomId -> Var -> Var -> [Var] -> Term -> [ModClause] -> a) -> BNF Token a
syn_duty_decl cons = "duty-type-decl" <:=> cons <$$>
  syn_is_closed <** keyword "Duty" <**> id_lit <** optional (keyword "With") <**
  keyword "Holder" <**> var <**
  keyword "Claimant" <**> var <**> 
  objects <**> syn_domain_constraint <**>
  syn_duty_clauses 

syn_act_decl :: (Bool -> DomId -> Maybe Var -> Maybe Var -> [Var] -> Term -> [ModClause] -> a) -> BNF Token a
syn_act_decl cons = "act-type-decl" <:=> cons <$$>
  syn_is_closed <** keyword "Act" <**> id_lit <** optional (keyword "With") <**>
  optional (keyword "Actor" **> var) <**> 
  optional (keyword "Recipient" **> var) <**> 
  objects <**> syn_domain_constraint <**> 
  syn_event_clauses 

syn_physical_decl :: (DomId -> Maybe Var -> [Var] -> Term -> [ModClause] -> a) -> BNF Token a
syn_physical_decl cons = "physical-type-decl" <:=> cons <$$
  keyword "Physical" <**> id_lit <** optional (keyword "With") <**>
  optional (keyword "Actor" **> var) <**> 
  objects <**> syn_domain_constraint <**> 
  syn_event_clauses 

syn_act_ext :: BNF Token Decl
syn_act_ext = "act-type-ext" <:=> TypeExt <$$ keyword "Act" <**> id_lit <**> syn_event_clauses 

syn_event_ext :: BNF Token Decl
syn_event_ext = "event-type-ext" <:=> TypeExt <$$ keyword "Event" <**> id_lit <**> syn_event_clauses 

syn_duty_ext :: BNF Token Decl
syn_duty_ext = "duty-type-ext" <:=> TypeExt <$$ keyword "Duty" <**> id_lit <**> syn_duty_clauses 

syn_event_decl :: (Bool -> DomId -> [Var] -> Term -> [ModClause] -> a) -> BNF Token a
syn_event_decl cons = "event-type-decl" <:=> cons <$$>
  syn_is_closed <** keyword "Event" <**> id_lit <** optional (keyword "With") <**>  
  objects <**> syn_domain_constraint <**> 
  syn_event_clauses

syn_fact_clauses :: BNF Token [ModClause]
syn_fact_clauses = multiple syn_fact_clause
 where syn_fact_clause = "fact-clause" <:=> ConditionedByCl <$$> precondition'
                                       <||> DerivationCl <$$> derivation_from
                                       <||> extend_domain_clauses

syn_physical_clauses :: BNF Token [ModClause]
syn_physical_clauses = multiple syn_physical_clause
  where syn_physical_clause = "physical-clause" <:=> ConditionedByCl <$$> precondition'
                                                <||> PostCondCl <$$> creating_post'
                                                <||> PostCondCl <$$> terminating_post'
                                                <||> PostCondCl <$$> obfuscating_post'
                                                <||> SyncCl <$$> synchronisations
  
syn_event_clauses :: BNF Token [ModClause]
syn_event_clauses = multiple syn_event_clause
  where syn_event_clause = "event-clause" <:=> ConditionedByCl <$$> precondition'
                                          <||> DerivationCl <$$> derivation_from
                                          <||> PostCondCl <$$> creating_post'
                                          <||> PostCondCl <$$> terminating_post'
                                          <||> PostCondCl <$$> obfuscating_post'
                                          <||> SyncCl <$$> synchronisations

syn_duty_clauses :: BNF Token [ModClause]
syn_duty_clauses = multiple syn_duty_clause
  where syn_duty_clause = "duty-clause" <:=> ConditionedByCl <$$> precondition'
                                        <||> DerivationCl <$$> derivation_from
                                        <||> ViolationCl <$$> violation_condition 
                                        <||> EnforcingActsCl <$$> enforcing_acts_clauses 
                                        <||> TerminatedByCl <$$> terminated_by_clauses 
                                        <||> CreatedByCl <$$> created_by_clauses 

objects :: BNF Token [Var]
objects = "related-to" <:=> optionalWithDef (keyword "Related to" **> multipleSepBy1 var (keychar ',')) []

enforcing_acts_clauses :: BNF Token [DomId]
enforcing_acts_clauses = "enforcing-act-clauses"
  <:=> keyword "Enforced by" **> multipleSepBy1 id_lit (keychar ',')

terminated_by_clauses :: BNF Token [DomId]
terminated_by_clauses = "terminated-by-clauses"
  <:=> keyword "Terminated by" **> multipleSepBy1 id_lit (keychar ',')

created_by_clauses :: BNF Token [DomId]
created_by_clauses = "created-by-clauses"
  <:=> keyword "Created by" **> multipleSepBy1 id_lit (keychar ',')

violation_condition :: BNF Token [Term]
violation_condition = "violation-conditions"
  <:=> keyword "Violated when" **> multipleSepBy1 value_expr (keychar ',')

precondition :: BNF Token [Term]
precondition = "preconditions" <:=> 
  optionalWithDef precondition' []
precondition' = keyword "Conditioned by" **> multipleSepBy value_expr (keychar ',') 

creating_post :: BNF Token [Effect]
creating_post = "creating-postcondition" <:=> 
  optionalWithDef creating_post' [] 
creating_post' = keyword "Creates" **> (map (uncurry CAll) <$$> multipleSepBy1 effect (keychar ','))

terminating_post :: BNF Token [Effect]
terminating_post = "terminating-postcondition" <:=>
  optionalWithDef terminating_post' []
terminating_post' = keyword "Terminates" **> (map (uncurry TAll) <$$> multipleSepBy1 effect (keychar ','))

obfuscating_post :: BNF Token [Effect]
obfuscating_post = "obfuscating-postcondition" <:=>
  optionalWithDef obfuscating_post' []
obfuscating_post' = keyword "Obfuscates" **> (map (uncurry OAll) <$$> multipleSepBy1 effect (keychar ','))


postconditions :: BNF Token [Effect]
postconditions = "postconditions" 
  <:=> (++) <$$> creating_post <**> terminating_post 
  <||> (++) <$$> terminating_post <**> creating_post

effect :: BNF Token ([Var], Term) 
effect = "effect-foreach" 
  <:=> ([],) <$$> value_expr 
  <||> foreach (,)

synchronisations :: BNF Token [Sync]
synchronisations = "synchronisations"
  <:=> keyword "Syncs with" **> multipleSepBy1 (opt_foreach Sync) (keychar ',')

application :: (DomId -> Arguments -> a) -> BNF Token a
application cons = "application" <:=> cons <$$> id_lit <**> arguments

foreach :: ([Var] -> Term -> a) -> BNF Token a
foreach cons = "foreach"
  <:=> parens (cons <$$ keyword "Foreach" <**> multipleSepBy1 var (keychar ',') 
                         <** keychar ':' <**> value_expr )

opt_foreach :: ([Var] -> Term -> a) -> BNF Token a
opt_foreach cons = "optional-foreach"
  <:=> cons [] <$$> value_expr 
  <||> foreach cons

derivation_from :: BNF Token [Derivation]
derivation_from = "derivation" 
  <:=> keyword "Derived from" **> multipleSepBy1 term_deriv (keychar ',')
  <||> map HoldsWhen <$$ keyword_present_when <**> multipleSepBy1 value_expr (keychar ',')
  where term_deriv = "term-derivation" <:=> Dv [] <$$> value_expr <||> foreach Dv 

keyword_present_when :: BNF Token String
keyword_present_when = "present-when"
  <:=> "Holds when" <$$ keyword "Present" <** keyword "When" 
  <||> "Holds when" <$$ keyword "Holds" <** keyword "When" 
  <||> "Holds when" <$$ keyword "Present when"
  <||> keyword "Holds when"

extend_domain_clauses :: BNF Token ModClause 
extend_domain_clauses = "extend-domain-clauses"
  <:=> keyword "Identified by" **> 
       (StringsCl <$$> manySepBy1 atom (keychar '+' <||> keychar ',')
  <||> IntsCl    <$$> manySepBy1 int_lit (keychar '+' <||> keychar ',')
  <||> ints_from_domain <$$> int_lit <** keyword ".." <**> int_lit
  <||> strings_from_domain <$$> char_lit <** keyword ".." <**> char_lit)
 where ints_from_domain min max = IntsCl $ [min..max]
       strings_from_domain min max = StringsCl $ map (:[]) [min..max]


-- parsing refiner specifications
parse_refiner :: String -> Either String Refiner
parse_refiner =  parse_component refiner

refiner :: BNF Token Refiner
refiner = "refinement" <:=> M.fromList <$$> multiple refine

refine :: BNF Token (DomId, Domain)
refine = "refine" <:=> (,) <$$ keyword "Fact" <**> id_lit <** keyword "Identified by" <**> type_expr

-- parsing initial state specifications
parse_initialiser :: String -> Either String Initialiser
parse_initialiser = parse_component initialiser 

initialiser :: BNF Token Initialiser
initialiser = "initial state" <:=> multiple (initial <** keychar '.') 
  where initial = "initial-statement" 
          <:=>  foreach CAll
          <||>  CAll [] <$$> value_expr


scenario :: BNF Token Scenario
scenario = "scenario" <:=> multiple statement

statement :: BNF Token Statement
statement = "statement"
  <:=> ($) <$$> actioner <**> maybe_action <** keychar '.'
  <||> Query <$$ keychar '?' <**> value_expr <** keychar '.'
  <||> Query . Not <$$ keyword "!?" <**> value_expr <** keychar '.'
  where actioner = "actioner" 
          <:=> (\(xs, d, ms) -> Trans xs Trigger (Right (d,ms)))  <$$ optional (keychar '!')
          <||> (\(xs, d, ms) -> Trans xs AddEvent (Right (d,ms))) <$$ keychar '+' 
          <||> (\(xs, d, ms) -> Trans xs RemEvent (Right (d,ms))) <$$ keychar '-'
          <||> (\(xs, d, ms) -> Trans xs ObfEvent (Right (d,ms))) <$$ keychar '~'   -- MISSING???
        maybe_action = "action-statement" 
            <:=> application ([],,)
            <||> parens ((\xs (d,args) -> (xs,d,args)) <$$ keyword "Foreach" <**> (multipleSepBy1 var (keychar ',')) <** keychar ':' <**> application (,))
 
phrase_scenario :: BNF Token [Phrase]
phrase_scenario = "phrase-scenario" <:=> multiple (syn_phrase <** keychar '.')

syn_directives_phrases :: BNF Token [Either Directive Phrase]
syn_directives_phrases = "opt.directives.phrases" <:=> top_level_unite <$$> optionalWithDef 
  (many1 (Left <$$> syn_directive <** keychar '.'
     <||> Right <$$> syn_phrase_or_comp)) [] 
      <**> (fmap Right <$$> optional syn_phrase) -- optional phrase *without* full stop

top_level_unite :: [a] -> Maybe a -> [a]
top_level_unite ps mp = maybe ps ((ps++) . (:[])) mp

syn_directive :: BNF Token Directive
syn_directive = "directive" <:=> 
       Include <$$ keyword "#include" <**> string_lit
  <||> Require <$$ keyword "#require" <**> string_lit

syn_phrases :: BNF Token [Phrase]
syn_phrases = syn_top_level 

syn_top_level :: BNF Token [Phrase]
syn_top_level = "top-level-phrases" <:=> top_level_unite <$$> 
  optionalWithDef (many1 syn_phrase_or_comp) [] <**> 
    optional syn_phrase -- optional phrase *without* full stop

syn_phrase_or_comp = "parallel-comp" <:=> 
  PParBlock <$$> braces ( optionalWithDef 
    (manySepBy1 syn_phrase (keychar '.') <** optional (keychar '.')) []
  ) <||> syn_phrase <** keychar '.'
 
syn_phrase :: BNF Token Phrase
syn_phrase = "phrase"
  <:=> optional (keychar '!') **> opt_foreach PTrigger 
  <||> keychar '+'  **> opt_foreach Create 
  <||> keychar '-'  **> opt_foreach Terminate
  <||> keychar '~'  **> opt_foreach Obfuscate 
  <||> PQuery <$$ keychar '?'  <**> value_expr 
  <||> PQuery . Not <$$ keyword "!?"  <**> value_expr 
  <||> keyword "?-" **> opt_foreach (PInstQuery False)
  <||> keyword "?--" **> opt_foreach (PInstQuery True)
  <||> PDeclBlock <$$> declarations 

